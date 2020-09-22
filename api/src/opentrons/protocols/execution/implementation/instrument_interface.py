from __future__ import annotations

from abc import abstractmethod, ABC
import typing

from opentrons import types
from opentrons.protocol_api.instrument_context import AdvancedLiquidHandling
from opentrons.protocol_api.labware import Well
from opentrons.protocols.advanced_control.transfers import TransferOptions


class InstrumentInterface(ABC):

    @abstractmethod
    def aspirate(self,
                 volume: float,
                 location: types.Location,
                 rate: float = 1.0) -> None:
        ...

    @abstractmethod
    def dispense(self,
                 volume: float,
                 location: types.Location,
                 rate: float = 1.0) -> None:
        ...

    @abstractmethod
    def mix(self,
            volume: float,
            location: types.Location,
            repetitions: int = 1,
            rate: float = 1.0) -> None:
        ...

    @abstractmethod
    def blow_out(self,
                 location: types.Location) -> None:
        ...

    @abstractmethod
    def touch_tip(self,
                  location: Well,
                  radius: float = 1.0,
                  v_offset: float = -1.0,
                  speed: float = 60.0) -> None:
        ...

    @abstractmethod
    def air_gap(self,
                location: types.Location,
                volume: float,
                height: float) -> None:
        ...

    @abstractmethod
    def return_tip(self,
                   home_after: bool = True) -> None:
        ...

    @abstractmethod
    def pick_up_tip(self,
                    location: types.Location,
                    presses: int = None,
                    increment: float = None) -> None:
        ...

    @abstractmethod
    def drop_tip(self,
                 location: types.Location,
                 home_after: bool = True) -> None:
        ...

    @abstractmethod
    def home(self) -> None:
        ...

    @abstractmethod
    def home_plunger(self) -> None:
        ...

    @abstractmethod
    def transfer(self,
                 volume: typing.Union[float, typing.Sequence[float]],
                 source: AdvancedLiquidHandling,
                 dest: AdvancedLiquidHandling,
                 mode: str,
                 transfer_options: TransferOptions) -> None:
        ...

    @abstractmethod
    def move_to(self,
                location: types.Location,
                force_direct: bool = False,
                minimum_z_height: float = None,
                speed: float = None) -> None:
        ...

    @abstractmethod
    def get_mount_name(self) -> str:
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...

    @abstractmethod
    def get_model(self) -> str:
        ...

    @abstractmethod
    def get_min_volume(self) -> float:
        ...

    @abstractmethod
    def get_max_volume(self) -> float:
        ...

    @abstractmethod
    def get_current_volume(self) -> float:
        ...

    @abstractmethod
    def get_available_volume(self) -> float:
        ...

    @abstractmethod
    def get_current_location(self) -> types.Location:
        """The current location of the pipette: (ie location cache)"""
        ...

    @abstractmethod
    def get_pipettes(self) -> typing.Dict[str, typing.Any]:
        ...

    @abstractmethod
    def get_channels(self) -> int:
        ...

    @abstractmethod
    def get_return_tip_height(self) -> int:
        ...
