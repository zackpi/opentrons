from __future__ import annotations

from abc import abstractmethod, ABC

from opentrons.hardware_control import API


class HardwareInterface(ABC):

    @abstractmethod
    def connect(self, hardware: API) -> None:
        ...

    @abstractmethod
    def disconnect(self, hardware: API) -> None:
        ...

    @abstractmethod
    def is_simulating(self, hardware: API) -> bool:
        ...

    @abstractmethod
    def set_rail_lights(self,
                        hardware: API,
                        on: bool) -> None:
        ...

    @abstractmethod
    def get_rail_lights_on(self,
                           hardware: API) -> bool:
        ...

    @abstractmethod
    def door_closed(self,
                    hardware: API) -> bool:
        ...
