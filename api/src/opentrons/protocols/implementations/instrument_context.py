import typing
from functools import lru_cache

from opentrons import types
from opentrons.calibration_storage import get
from opentrons.calibration_storage.types import TipLengthCalNotFound
from opentrons.config.feature_flags import enable_calibration_overhaul
from opentrons.hardware_control import CriticalPoint
from opentrons.protocols.api_support.labware_like import LabwareLike
from opentrons.protocols.api_support.util import Clearances, build_edges
from opentrons.protocols.geometry import planning
from opentrons.protocols.implementations.interfaces.instrument_context import \
    InstrumentContextInterface
from opentrons.protocols.implementations.interfaces.labware import \
    LabwareInterface
from opentrons.protocols.implementations.interfaces.protocol_context import \
    ProtocolContextInterface
from opentrons.protocols.implementations.well import WellImplementation
from opentrons.protocols.types import APIVersion


class InstrumentContextImplementation(InstrumentContextInterface):
    """Implementation of the InstrumentContext interface."""

    _api_version: APIVersion
    _protocol_interface: ProtocolContextInterface
    _tip_racks: typing.List[LabwareInterface]
    _mount: types.Mount
    _instrument_name: str
    _starting_tip: typing.Optional[WellImplementation]
    _default_speed: float
    _well_bottom_clearances: Clearances

    def __init__(self,
                 api_version: APIVersion,
                 protocol_interface: ProtocolContextInterface,
                 tip_racks: typing.List[LabwareInterface],
                 mount: types.Mount,
                 instrument_name: str,
                 default_speed: float):
        """"Constructor"""
        self._api_version = api_version
        self._protocol_interface = protocol_interface
        self._tip_racks = tip_racks
        self._mount = mount
        self._instrument_name = instrument_name
        self._default_speed = default_speed
        self._well_bottom_clearances = Clearances(
            default_aspirate=1.0,
            default_dispense=1.0
        )

    def get_api_version(self) -> APIVersion:
        """Get the API Version for this context's protocol."""
        # TODO AL 20201110 - Remove need for api_version in this module
        return self._api_version

    def get_starting_tip(self) -> typing.Optional[WellImplementation]:
        """Gets the starting tip."""
        return self._starting_tip

    def set_starting_tip(self, location: typing.Optional[WellImplementation]):
        """Sets the starting tip."""
        self._starting_tip = location

    def reset_tipracks(self) -> None:
        """Reload all tips in each tip rack and reset starting tip."""
        for tiprack in self.get_tip_racks():
            tiprack.reset_tips()
        self.set_starting_tip(None)

    def get_default_speed(self) -> float:
        """Gets the speed at whcih the robot's gandry moves."""
        return self._default_speed

    def set_default_speed(self, speed: float) -> None:
        """Sets the speed at whcih the robot's gandry moves."""
        self._default_speed = speed

    def aspirate(self,
                 volume: float,
                 location: types.Location,
                 rate: float = 1.0) -> None:
        """Aspirate a given volume of liquid from the specified location, using
        this pipette."""
        self._protocol_interface.get_hardware().hardware.aspirate(
            self._mount, volume, rate
        )

    def dispense(self, volume: float, location: types.Location,
                 rate: float = 1.0) -> None:
        """Dispense a volume of liquid (in microliters/uL) using this pipette
        into the specified location."""
        self._protocol_interface.get_hardware().hardware.dispense(
            self._mount, volume, rate
        )

    def blow_out(self, location: types.Location) -> None:
        """Blow liquid out of the tip."""
        self._protocol_interface.get_hardware().hardware.blow_out(self._mount)

    def touch_tip(self,
                  location: WellImplementation,
                  radius: float = 1.0,
                  v_offset: float = -1.0,
                  speed: float = 60.0) -> None:
        """
        Touch the pipette tip to the sides of a well, with the intent of
        removing left-over droplets
        """
        # TODO al 20201110 - build_edges relies on where being a Well. This is
        #  an unpleasant compromise until refactoring build_edges to support
        #  WellImplementation.
        #  Also, build_edges should not require api_version.
        from opentrons.protocol_api.labware import Well

        edges = build_edges(
            where=Well(well_implementation=location,
                       api_level=self.get_api_version()),
            offset=v_offset,
            mount=self._mount,
            deck=self._protocol_interface.get_deck(),
            radius=radius,
            version=self.get_api_version()
        )
        for edge in edges:
            self._protocol_interface.get_hardware().hardware.move_to(
                self._mount,
                edge,
                speed
            )

    def pick_up_tip(self,
                    well: WellImplementation,
                    presses: int = None,
                    increment: float = None) -> None:
        """Pick up a tip for the pipette to run liquid-handling commands."""
        hw = self._protocol_interface.get_hardware().hardware
        geometry = well.get_geometry()

        hw.set_current_tiprack_diameter(
            self._mount, geometry.diameter)

        hw.hardware.pick_up_tip(
            self._mount,
            self._tip_length_for(geometry.parent),
            presses,
            increment
        )
        hw.hardware.set_working_volume(
            self._mount, geometry.max_volume)

    def drop_tip(self,
                 location: types.Location,
                 home_after: bool = True) -> None:
        """Drop the tip."""
        self._protocol_interface.get_hardware().hardware.drop_tip(
            self._mount,
            home_after=home_after
        )

    def home(self) -> None:
        """Home the mount"""
        self._protocol_interface.get_hardware().hardware.home_z(self._mount)
        self.home_plunger()

    def home_plunger(self) -> None:
        """Home the plunger associated with this mount."""
        self._protocol_interface.get_hardware().hardware.home_plunger(
            self._mount
        )

    def delay(self) -> None:
        """Delay protocol execution."""
        self._protocol_interface.delay()

    def move_to(self,
                location: types.Location,
                force_direct: bool = False,
                minimum_z_height: float = None,
                speed: float = None) -> None:
        """Move the instrument."""
        if self._location_cache.location_labware:
            from_lw = self._location_cache.location_labware
        else:
            from_lw = LabwareLike(None)

        if not speed:
            speed = self.get_default_speed()

        from_center = from_lw.center_multichannel_on_wells() \
            if from_lw else False
        cp_override = CriticalPoint.XY_CENTER if from_center else None
        from_loc = types.Location(
            self._protocol_interface.get_hardware().hardware.gantry_position(
                self._mount, critical_point=cp_override),
            from_lw)

        for mod in self._protocol_interface.get_loaded_instruments().values():
            if isinstance(mod, ThermocyclerContext):
                mod.flag_unsafe_move(to_loc=location, from_loc=from_loc)

        instr_max_height = self._protocol_interface.get_hardware().hardware.get_instrument_max_height(self._mount)
        moves = planning.plan_moves(from_loc, location,
                                    self._protocol_interface.get_deck(),
                                    instr_max_height,
                                    force_direct=force_direct,
                                    minimum_z_height=minimum_z_height
                                    )
        self._log.debug("move_to: {}->{} via:\n\t{}"
                        .format(from_loc, location, moves))
        try:
            for move in moves:
                self._protocol_interface.get_hardware().hardware.move_to(
                    self._mount, move[0], critical_point=move[1], speed=speed,
                    max_speeds=self._protocol_interface.get_max_speeds().data)
        except Exception:
            self._location_cache.clear()
            raise
        else:
            self._location_cache.location = location

    def get_mount(self) -> types.Mount:
        """Get the mount this pipette is attached to."""
        return self._mount

    def get_tip_racks(self) -> typing.List[LabwareInterface]:
        """Get the tip racks that have been linked to this pipette."""
        return self._tip_racks

    def set_tip_racks(self, racks: typing.List[LabwareInterface]) -> None:
        """Set the tip racks that have been linked to this pipette."""
        self._tip_racks = racks

    def get_instrument_name(self) -> str:
        """Get the instrument name."""
        return self._instrument_name

    def get_pipette_name(self) -> str:
        """Get the pipette name."""
        return self.get_pipette()['name']

    def get_model(self) -> str:
        """Get the model name."""
        return self.get_pipette()['model']

    def get_min_volume(self) -> float:
        """Get the min volume."""
        return self.get_pipette()['min_volume']

    def get_max_volume(self) -> float:
        """Get the max volume."""
        return self.get_pipette()['max_volume']

    def get_current_volume(self) -> float:
        """Get the current volume."""
        return self.get_pipette()['current_volume']

    def get_available_volume(self) -> float:
        """Get the available volume."""
        return self.get_pipette()['available_volume']

    def get_current_location(self) -> types.Location:
        pass

    def get_pipette(self) -> typing.Dict[str, typing.Any]:
        """Get the hardweare pipette dictionary."""
        hw_manager = self._protocol_interface.get_hardware()
        pipette = hw_manager.hardware.attached_instruments[self._mount]
        if pipette is None:
            raise types.PipetteNotAttachedError
        return pipette

    def get_channels(self) -> int:
        """Number of channels."""
        return self.get_pipette()['channels']

    def has_tip(self) -> bool:
        """Whether a tip is attached."""
        return self.get_pipette()['has_tip']

    def get_return_height(self) -> float:
        """The height to return a tip to its tiprack."""
        return self.get_pipette().get('return_tip_height', 0.5)

    def get_well_bottom_clearance(self) -> Clearances:
        """The distance above the bottom of a well to aspirate or dispense."""
        return self._well_bottom_clearances

    @lru_cache(maxsize=12)
    def _tip_length_for(self, tiprack: LabwareInterface) -> float:
        """ Get the tip length, including overlap, for a tip from this rack """

        def _build_length_from_overlap() -> float:
            tip_overlap = self.get_pipette()['tip_overlap'].get(
                tiprack.get_uri(),
                self.get_pipette()['tip_overlap']['default'])
            tip_length = tiprack.get_tip_length()
            return tip_length - tip_overlap

        if not enable_calibration_overhaul():
            return _build_length_from_overlap()
        else:
            try:
                from opentrons.protocol_api.labware import Labware
                # TODO AL 20201110 - Make LabwareLike interact with
                #  LabwareInterface instead of Labware
                parent = LabwareLike(Labware(implementation=tiprack,
                                             api_level=self.get_api_version())
                                     ).first_parent() or ''
                return get.load_tip_length_calibration(
                    self.get_pipette()['pipette_id'],
                    tiprack.get_definition(),
                    parent)['tipLength']
            except TipLengthCalNotFound:
                return _build_length_from_overlap()
