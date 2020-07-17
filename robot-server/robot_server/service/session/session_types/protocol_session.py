from .base_session import BaseSession
from .. import models
from ..command_execution import CommandQueue, CommandExecutor
from ..errors import UnsupportedFeature


class ProtocolSession(BaseSession):
    def _get_response_details(self) -> models.SessionDetails:
        pass

    @property
    def command_executor(self) -> CommandExecutor:
        pass

    @property
    def command_queue(self) -> CommandQueue:
        raise UnsupportedFeature()

    @property
    def session_type(self) -> models.SessionType:
        return models.SessionType.protocol
