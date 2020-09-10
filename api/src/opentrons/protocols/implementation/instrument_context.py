import logging
import typing
from typing import List, Union

from opentrons import types, commands as cmds, hardware_control as hc
from opentrons.broker import Broker
from opentrons.commands import CommandPublisher
from opentrons.protocol_api.instrument_context import AdvancedLiquidHandling
from opentrons.protocol_api.labware import Labware, Well
from opentrons.protocols.advanced_control.transfers import TransferOptions
from opentrons.protocols.api_support.util import FlowRates, PlungerSpeeds, \
    Clearances, HardwareManager
from opentrons.protocols.implementation.interfaces.instrument_context import \
    AbstractInstrumentContextImpl
from opentrons.protocols.implementation.interfaces.protocol_context import \
    AbstractProtocolContext
from opentrons.protocols.implementation.location_cache import LocationCache
from opentrons.protocols.types import APIVersion


class InstrumentContextImplementation(AbstractInstrumentContextImpl,
                                      CommandPublisher):

    def __init__(self,
                 ctx: AbstractProtocolContext,
                 broker: Broker,
                 location_cache: LocationCache,
                 hardware_mgr: 'HardwareManager',
                 mount: types.Mount,
                 log_parent: logging.Logger,
                 at_version: APIVersion,
                 tip_racks: List[Labware] = None,
                 trash: Labware = None,
                 default_speed: float = 400.0,
                 requested_as: str = None,
                 **config_kwargs) -> None:

        super().__init__(broker)
        self._api_version = at_version
        self._hw_manager = hardware_mgr
        self._ctx = ctx
        self._mount = mount
        self._log = log_parent.getChild(repr(self))

        self._tip_racks = tip_racks or list()
        for tip_rack in self.tip_racks:
            assert tip_rack.is_tiprack
            self._validate_tiprack(tip_rack)
        if trash is None:
            self.trash_container = self._ctx.get_fixed_trash()
        else:
            self.trash_container = trash

        self._default_speed = default_speed

        self._last_location: Union[Labware, Well, None] = None
        self._last_tip_picked_up_from: Union[Well, None] = None
        self._well_bottom_clearance = Clearances(
            default_aspirate=1.0, default_dispense=1.0)
        self._flow_rates = FlowRates(self)
        self._speeds = PlungerSpeeds(self)
        self._starting_tip: Union[Well, None] = None
        self.requested_as = requested_as
        self._flow_rates.set_defaults(self._api_version)
        self._location_cache = location_cache

    def get_hardware(self) -> HardwareManager:
        return self._hw_manager

    def get_api_version(self) -> APIVersion:
        return self._api_version

    def get_starting_tip(self) -> typing.Optional[Well]:
        return self._starting_tip

    def set_starting_tip(self, location: typing.Optional[Well]):
        self._starting_tip = location

    def reset_tipracks(self) -> None:
        for tiprack in self._tip_racks:
            tiprack.reset()
        self.set_starting_tip(None)

    def get_default_speed(self) -> float:
        return self._default_speed

    def set_default_speed(self, speed: float) -> None:
        self._default_speed = speed

    def aspirate(self,
                 volume: float,
                 location: types.Location,
                 rate: float = 1.0) -> None:
        pass

    def dispense(self,
                 volume: float,
                 location: types.Location,
                 rate: float = 1.0) -> None:
        pass

    def mix(self,
            volume: float,
            location: types.Location,
            repetitions: int = 1,
            rate: float = 1.0) -> None:
        pass

    def blow_out(self,
                 location: types.Location) -> None:
        pass

    def touch_tip(self,
                  location: Well,
                  radius: float = 1.0,
                  v_offset: float = -1.0,
                  speed: float = 60.0) -> None:
        pass

    def air_gap(self,
                volume: float,
                height: float) -> None:
        pass

    def return_tip(self,
                   home_after: bool = True) -> None:
        pass

    def pick_up_tip(self,
                    location: types.Location,
                    presses: int = None,
                    increment: float = None) -> None:
        pass

    def drop_tip(self,
                 location: types.Location,
                 home_after: bool = True) -> None:
        pass

    def home(self) -> None:
        pass

    def home_plunger(self) -> None:
        pass

    def transfer(self,
                 volume: typing.Union[float, typing.Sequence[float]],
                 source: AdvancedLiquidHandling,
                 dest: AdvancedLiquidHandling,
                 mode: str,
                 transfer_options: TransferOptions) -> None:
        pass

    def delay(self) -> None:
        pass

    def move_to(self,
                location: types.Location,
                force_direct: bool = False,
                minimum_z_height: float = None,
                speed: float = None) -> None:
        pass

    def get_mount_name(self) -> str:
        pass

    def get_speed(self) -> PlungerSpeeds:
        pass

    def get_flow_rate(self) -> FlowRates:
        pass

    def get_type(self) -> str:
        pass

    def get_tip_racks(self) -> typing.List[Labware]:
        pass

    def set_tip_racks(self, racks: typing.List[Labware]):
        pass

    def get_trash_container(self) -> Labware:
        pass

    def set_trash_container(self, trash: Labware):
        pass

    def get_name(self) -> str:
        pass

    def get_model(self) -> str:
        pass

    def get_min_volume(self) -> float:
        pass

    def get_max_volume(self) -> float:
        pass

    def get_current_volume(self) -> float:
        pass

    def get_available_volume(self) -> float:
        return self.get_pipette()['current_volume']

    def get_current_location(self) -> typing.Optional[types.Location]:
        pass

    def get_pipette(self) -> typing.Dict[str, typing.Any]:
        pipette = self._hw_manager.hardware.attached_instruments[self._mount]
        if pipette is None:
            raise types.PipetteNotAttachedError
        return pipette

    def get_channels(self) -> int:
        return self.get_pipette()['channels']

    def get_return_height(self) -> int:
        return self.get_pipette().get('return_tip_height', 0.5)

    def get_well_bottom_clearance(self) -> Clearances:
        return self._well_bottom_clearance
