from abc import ABC, abstractmethod


class FlowInterface(ABC):

    @abstractmethod
    def pause(self,
              msg: str = None) -> None:
        ...

    @abstractmethod
    def resume(self) -> None:
        ...

    @abstractmethod
    def delay(self,
              seconds: int,
              msg: str = None) -> None:
        ...

    @abstractmethod
    def comment(self,
                msg: str) -> None:
        ...
