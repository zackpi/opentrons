import asyncio
import logging
from typing import Dict, Optional, List, Set

from opentrons import types, API
from opentrons.config import feature_flags as fflags
from opentrons.drivers.mag_deck import MagDeck
from opentrons.drivers.temp_deck import TempDeck
from opentrons.drivers.thermocycler import Thermocycler
from opentrons.hardware_control import ExecutionManager
from opentrons.hardware_control.types import DoorState
from opentrons.protocols.api_support.definitions import MAX_SUPPORTED_VERSION
from opentrons.protocols.geometry.deck import Deck
from opentrons.protocols.geometry import module_geometry
from opentrons.protocols.implementations.instrument_context import \
    InstrumentContextImplementation
from opentrons.protocols.implementations.interfaces.instrument_context import \
    InstrumentContextInterface
from opentrons.protocols.implementations.interfaces.labware import \
    LabwareInterface
from opentrons.protocols.implementations.interfaces.protocol_context import \
    ProtocolContextInterface, InstrumentDict, LoadModuleResult
from opentrons.protocols.api_support.util import (
    AxisMaxSpeeds, HardwareToManage, HardwareManager)
from opentrons.protocols.labware import load_from_definition, \
    get_labware_definition
from opentrons.protocols.types import Protocol, APIVersion
from opentrons_shared_data.labware import LabwareDefinition


MODULE_LOG = logging.getLogger(__name__)

SHORT_TRASH_DECK = 'ot2_short_trash'
STANDARD_DECK = 'ot2_standard'


class ProtocolContextImplementation(ProtocolContextInterface):

    def __init__(self,
                 api_version: APIVersion = MAX_SUPPORTED_VERSION,
                 loop: asyncio.AbstractEventLoop = None,
                 hardware: HardwareToManage = None,
                 bundled_labware: Dict[str, LabwareDefinition] = None,
                 bundled_data: Dict[str, bytes] = None,
                 extra_labware: Dict[str, LabwareDefinition] = None,
                 ) -> None:
        """
        Constructor

        :param api_version: The API version used by the protocol.
        :param loop: event loop. default loop will be used if None.
        :param hardware: hardware instance. will use simulator if None.
        :param bundled_labware: optional bundled labware definitions.
        :param bundled_data: optional bundled data.
        :param extra_labware: optional extra labware definitions.
        """
        self._api_version = api_version
        self._loop = loop or asyncio.get_event_loop()
        deck_load_name = SHORT_TRASH_DECK if fflags.short_fixed_trash() \
            else STANDARD_DECK
        self._deck_layout = Deck(load_name=deck_load_name)
        self._instruments: InstrumentDict = {
            mount: None for mount in types.Mount
        }
        self._modules: Set[LoadModuleResult] = set()

        self._hw_manager = HardwareManager(hardware)
        self._log = MODULE_LOG.getChild(self.__class__.__name__)

        self._bundled_labware = bundled_labware
        self._extra_labware = extra_labware or {}

        self._bundled_data: Dict[str, bytes] = bundled_data or {}
        self._default_max_speeds = AxisMaxSpeeds()
        self._last_location: Optional[types.Location] = None

    @classmethod
    def build_using(cls,
                    protocol: Protocol,
                    *args, **kwargs):
        """ Build an API instance for the specified parsed protocol

        This is used internally to provision the context with bundle
        contents or api levels.
        """
        kwargs['bundled_data'] = getattr(protocol, 'bundled_data', None)
        kwargs['bundled_labware'] = getattr(protocol, 'bundled_labware', None)
        return cls(*args, **kwargs)

    def get_api_version(self) -> APIVersion:
        """Get the API version."""
        # TODO AL 20201110 - Find a way to omit api_version from this class.
        #  it is used in creating module geometry and instrument context.
        return self._api_version

    def get_bundled_data(self) -> Dict[str, bytes]:
        """Extra bundled data."""
        # TODO AL 20201110 - This should be removed along with the bundling
        #  feature as we move to HTTP based protocol execution.
        return self._bundled_data

    def get_bundled_labware(self) -> Optional[Dict[str, LabwareDefinition]]:
        """Bundled labware defintion."""
        # TODO AL 20201110 - This should be removed along with the bundling
        #  feature as we move to HTTP based protocol execution.
        return self._bundled_labware

    def get_extra_labware(self) -> Optional[Dict[str, LabwareDefinition]]:
        """Extra labware definitions."""
        return self._extra_labware

    def cleanup(self) -> None:
        """Protocol context clean up."""
        pass

    def get_max_speeds(self) -> AxisMaxSpeeds:
        """Get the maximum axis speeds."""
        return self._default_max_speeds

    def get_hardware(self) -> HardwareManager:
        """Access to the hardware manager."""
        return self._hw_manager

    def connect(self, hardware: API) -> None:
        """Connect to the hardware."""
        self._hw_manager.set_hw(hardware)
        self._hw_manager.hardware.cache_instruments()

    def disconnect(self) -> None:
        """"Disconnect from the hardware."""
        self._hw_manager.reset_hw()

    def is_simulating(self) -> bool:
        """Returns true if hardware is being simulated."""
        return self._hw_manager.hardware.is_simulator

    def load_labware_from_definition(
            self,
            labware_def: LabwareDefinition,
            location: types.DeckLocation,
            label: str = None) -> LabwareInterface:
        """Load a labware from definition"""
        parent = self.get_deck().position_for(location)
        labware_obj = load_from_definition(labware_def, parent, label)
        self._deck_layout[location] = labware_obj
        return labware_obj

    def load_labware(
            self,
            load_name: str,
            location: types.DeckLocation,
            label: str = None,
            namespace: str = None,
            version: int = None) -> LabwareInterface:
        """Load a labware."""
        labware_def = get_labware_definition(
            load_name, namespace, version,
            bundled_defs=self._bundled_labware,
            extra_defs=self._extra_labware)
        return self.load_labware_from_definition(
            labware_def, location, label)

    def load_module(
            self,
            module_name: str,
            location: Optional[types.DeckLocation] = None,
            configuration: str = None) -> Optional[LoadModuleResult]:
        """Load a module."""
        resolved_model = module_geometry.resolve_module_model(module_name)
        resolved_type = module_geometry.resolve_module_type(resolved_model)
        resolved_location = self._deck_layout.resolve_module_location(
            resolved_type, location)

        # Load the geometry
        geometry = module_geometry.load_module(
            model=resolved_model,
            parent=self._deck_layout.position_for(resolved_location),
            api_level=self._api_version,
            configuration=configuration)

        # Try to find in the hardware instance
        hc_mod_instance = None
        for mod in self._hw_manager.hardware.attached_modules:
            if module_geometry.models_compatible(
                    module_geometry.module_model_from_string(mod.model()),
                    resolved_model):
                hc_mod_instance = mod
                break

        if self.is_simulating() and hc_mod_instance is None:
            mod_type = {
                module_geometry.ModuleType.MAGNETIC: MagDeck,
                module_geometry.ModuleType.TEMPERATURE: TempDeck,
                module_geometry.ModuleType.THERMOCYCLER: Thermocycler
                }[resolved_type]
            hc_mod_instance = mod_type(
                port='',
                simulating=True,
                loop=self._hw_manager.hardware.loop,
                execution_manager=ExecutionManager(
                    loop=self._hw_manager.hardware.loop),
                sim_model=resolved_model.value)

        if not hc_mod_instance:
            return None

        result = LoadModuleResult(type=resolved_type,
                                  geometry=geometry,
                                  module=hc_mod_instance)

        self._modules.add(result)
        self._deck_layout[resolved_location] = geometry
        return result

    def get_loaded_modules(self) -> Dict[int, LoadModuleResult]:
        """Get a mapping of deck location to loaded module."""
        return {int(str(module.geometry.parent)): module
                for module in self._modules}

    def load_instrument(self,
                        instrument_name: str,
                        mount: types.Mount,
                        tip_racks: List[LabwareInterface] = None,
                        replace: bool = False) -> InstrumentContextInterface:
        """Load an instrument."""
        instr = self._instruments[mount]
        if instr and not replace:
            raise RuntimeError(
                f"Instrument already present in {mount.name.lower()} "
                f"mount: {instr.get_instrument_name()}")

        attached = {att_mount: instr.get('name', None)
                    for att_mount, instr
                    in self._hw_manager.hardware.attached_instruments.items()
                    if instr}
        attached[mount] = instrument_name
        self._hw_manager.hardware.cache_instruments(attached)
        # If the cache call didn’t raise, the instrument is attached
        new_instr = InstrumentContextImplementation(
            api_version=self.get_api_version(),
            protocol_interface=self,
            mount=mount,
            instrument_name=instrument_name,
            default_speed=400.0
        )
        self._instruments[mount] = new_instr
        self._log.info("Instrument {} loaded".format(new_instr))
        return new_instr

    def get_loaded_instruments(self) -> InstrumentDict:
        """Get a mapping of mount to instrument."""
        return self._instruments

    def pause(self, msg: str = None) -> None:
        """Pause the protocol."""
        self._hw_manager.hardware.pause()

    def resume(self) -> None:
        """Result the protocol."""
        self._hw_manager.hardware.resume()

    def comment(self, msg: str) -> None:
        """Add comment to run log."""
        pass

    def delay(self, seconds=0, msg: str = None) -> None:
        """Delay execution for x seconds."""
        self._hw_manager.hardware.delay(seconds)

    def home(self) -> None:
        """Home the robot."""
        self._location_cache.clear()
        self._hw_manager.hardware.home()

    def get_deck(self) -> Deck:
        """Get the deck layout."""
        return self._deck_layout

    def set_rail_lights(self, on: bool) -> None:
        """Set the rail light state."""
        self._hw_manager.hardware.set_lights(rails=on)

    def get_rail_lights_on(self) -> bool:
        """Get the rail light state."""
        return self._hw_manager.hardware.get_lights()['rails']

    def door_closed(self) -> bool:
        """Check if door is closed."""
        return DoorState.CLOSED == self._hw_manager.hardware.door_state

    def get_last_location(self) -> Optional[types.Location]:
        """Get the most recent moved to location."""
        return self._last_location

    def set_last_location(self, location: Optional[types.Location]) -> None:
        """Set the most recent moved to location."""
        self._last_location = location
