from abc import ABC, abstractmethod
from typing import Dict

from opentrons.protocol_api.labware import Labware
from opentrons.protocols.types import APIVersion
from opentrons.types import Location
from opentrons_shared_data.labware import LabwareDefinition


class LabwareInterface(ABC):
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
