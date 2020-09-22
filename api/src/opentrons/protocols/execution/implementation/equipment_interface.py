from abc import ABC, abstractmethod
from typing import Dict, Optional

from opentrons import types, API
from opentrons.protocol_api.labware import Labware
from opentrons.protocols.execution.implementation.instrument_interface import \
    InstrumentInterface
from opentrons.protocols.execution.implementation.magnetic_interface import \
    MagneticInterface
from opentrons.protocols.execution.implementation.temperature_interface \
    import TemperatureInterface
from opentrons.protocols.execution.implementation.thermocycler_interface \
    import ThermocyclerInterface
from opentrons.protocols.types import APIVersion
from opentrons.types import Location
from opentrons_shared_data.labware import LabwareDefinition


class EquipmentInterface(ABC):

    @abstractmethod
    def load_from_definition(
            self,
            definition: LabwareDefinition,
            parent: Location,
            label: str = None,
            api_level: APIVersion = None) \
            -> Labware:
        ...

    @abstractmethod
    def get_definition(
            self,
            load_name: str,
            namespace: str = None,
            version: int = None,
            bundled_defs: Dict[str, LabwareDefinition] = None,
            extra_defs: Dict[str, LabwareDefinition] = None) \
            -> LabwareDefinition:
        ...

    @abstractmethod
    def load_instrument(
            self,
            hardware: API,
            instrument_name: str,
            mount: types.Mount,
            replace: bool = False) -> InstrumentInterface:
        ...

    @abstractmethod
    def load_magnetic(
            self,
            hardware: API,
            model: str,
            location: Optional[types.DeckLocation] = None) \
            -> MagneticInterface:
        ...

    @abstractmethod
    def load_temperature(
            self,
            hardware: API,
            model: str,
            location: Optional[types.DeckLocation] = None) \
            -> TemperatureInterface:
        ...

    @abstractmethod
    def load_thermocycler(
            self,
            hardware: API,
            model: str,
            configuration: Optional[str] = None) \
            -> ThermocyclerInterface:
        ...
