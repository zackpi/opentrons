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
    Clearances, HardwareManager, clamp_value, build_edges
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
        self._trash: typing.Optional[Labware] = None

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
        c_vol = self.get_pipette()['available_volume'] if not volume else volume

        cmds.do_publish(self.broker, cmds.aspirate, self.aspirate,
                        'before', None, None, self, c_vol, location, rate)
        self._hw_manager.hardware.aspirate(self._mount, volume, rate)
        cmds.do_publish(self.broker, cmds.aspirate, self.aspirate,
                        'after', self, None, self, c_vol, location, rate)

    def dispense(self,
                 volume: float,
                 location: types.Location,
                 rate: float = 1.0) -> None:
        c_vol = self.get_pipette()['current_volume'] if not volume else volume

        cmds.do_publish(self.broker, cmds.dispense, self.dispense,
                        'before', None, None, self, c_vol, location, rate)
        self._hw_manager.hardware.dispense(self._mount, volume, rate)
        cmds.do_publish(self.broker, cmds.dispense, self.dispense,
                        'after', self, None, self, c_vol, location, rate)

    def mix(self,
            volume: float,
            location: types.Location,
            repetitions: int = 1,
            rate: float = 1.0) -> None:
        c_vol = self.get_pipette()['available_volume'] if not volume else volume

        cmds.do_publish(self.broker, cmds.mix, self.mix,
                        'before', None, None,
                        self, repetitions, c_vol, location)
        self.aspirate(volume, location, rate)
        while repetitions - 1 > 0:
            self.dispense(volume, rate=rate, location=location)
            self.aspirate(volume, rate=rate, location=location)
            repetitions -= 1
        self.dispense(volume, rate=rate, location=location)
        cmds.do_publish(self.broker, cmds.mix, self.mix,
                        'after', None, None,
                        self, repetitions, c_vol, location)

    def blow_out(self) -> None:
        self._hw_manager.hardware.blow_out(self._mount)

    def touch_tip(self,
                  location: Well,
                  radius: float = 1.0,
                  v_offset: float = -1.0,
                  speed: float = 60.0) -> None:
        edges = build_edges(
            location, v_offset, self._api_version,
            self._mount, self._ctx.get_deck(), radius)
        for edge in edges:
            self._hw_manager.hardware.move_to(self._mount, edge, speed)

    def air_gap(self,
                location: types.Location,
                volume: float,
                height: float) -> None:
        target = location.labware.top(height)
        self.move_to(target)
        self.aspirate(volume, location=location)

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
        def home_dummy(mount): pass

        cmds.do_publish(self.broker, cmds.home, home_dummy,
                        'before', None, None, self._mount.name.lower())
        self._hw_manager.hardware.home_z(self._mount)
        self._hw_manager.hardware.home_plunger(self._mount)
        cmds.do_publish(self.broker, cmds.home, home_dummy,
                        'after', self, None, self._mount.name.lower())

    def home_plunger(self) -> None:
        self._hw_manager.hardware.home_plunger(self._mount)

    def transfer(self,
                 volume: typing.Union[float, typing.Sequence[float]],
                 source: AdvancedLiquidHandling,
                 dest: AdvancedLiquidHandling,
                 mode: str,
                 transfer_options: TransferOptions) -> None:
        pass

    def delay(self) -> None:
        self._ctx.delay()

    def move_to(self,
                location: types.Location,
                force_direct: bool = False,
                minimum_z_height: float = None,
                speed: float = None) -> None:
        pass

    def get_mount_name(self) -> str:
        return self._mount.name.lower()

    def get_speed(self) -> PlungerSpeeds:
        return self._speeds

    def get_flow_rate(self) -> FlowRates:
        return self._flow_rates

    def get_type(self) -> str:
        model = self.get_name()
        if 'single' in model:
            return 'single'
        elif 'multi' in model:
            return 'multi'
        else:
            raise RuntimeError("Bad pipette name: {}".format(model))

    def get_tip_racks(self) -> typing.List[Labware]:
        return self._tip_racks

    def set_tip_racks(self, racks: typing.List[Labware]):
        self._tip_racks = racks

    def get_trash_container(self) -> typing.Optional[Labware]:
        return self._trash

    def set_trash_container(self, trash: Labware):
        self._trash = trash

    def get_name(self) -> str:
        return self.get_pipette()['name']

    def get_model(self) -> str:
        return self.get_pipette()['model']

    def get_min_volume(self) -> float:
        return self.get_pipette()['min_volume']

    def get_max_volume(self) -> float:
        return self.get_pipette()['max_volume']

    def get_current_volume(self) -> float:
        return self.get_pipette()['current_volume']

    def get_available_volume(self) -> float:
        return self.get_pipette()['available_volume']

    def get_current_location(self) -> typing.Optional[types.Location]:
        return self._location_cache.location

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
