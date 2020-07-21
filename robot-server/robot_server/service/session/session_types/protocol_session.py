import asyncio
import logging
from threading import Thread
from queue import Queue
import os
import sys

from opentrons import ThreadManager
from opentrons.api import Session
from opentrons.broker import Broker, Notifications
from opentrons.hardware_control import ThreadedAsyncLock

from robot_server.util import duration
from . import SessionMetaData
from .base_session import BaseSession
from .. import models
from ..command_execution import CommandQueue, CommandExecutor, Command, \
    CompletedCommand, CommandResult
from ..configuration import SessionConfiguration
from ..errors import UnsupportedFeature, SessionCreationException, \
    UnsupportedCommandException
from ..models import EmptyModel
from ...protocol.errors import ProtocolNotFoundException
from ...protocol.protocol import UploadedProtocol


log = logging.getLogger(__name__)


class ProtocolSession(BaseSession, CommandExecutor):

    def __init__(self,
                 configuration: SessionConfiguration,
                 instance_meta: SessionMetaData,
                 protocol: UploadedProtocol):
        """
        Constructor

        :param configuration:
        :param instance_meta:
        :param protocol:
        """
        super().__init__(configuration, instance_meta)
        self._handlers = {
            models.ProtocolCommand.run: self.handle_run,
            models.ProtocolCommand.simulate: self.handle_simulate,
            models.ProtocolCommand.cancel: self.handle_cancel,
            models.ProtocolCommand.resume: self.handle_resume,
            models.ProtocolCommand.pause: self.handle_pause,
        }
        self._uploaded_protocol = protocol
        self._th = None

    @classmethod
    async def create(cls, configuration: SessionConfiguration,
                     instance_meta: SessionMetaData) -> 'BaseSession':
        """Try to create the protocol session"""
        try:
            protocol = configuration.protocol_manager.get(
                instance_meta.create_params.name
            )
            return cls(configuration, instance_meta, protocol)
        except ProtocolNotFoundException as e:
            raise SessionCreationException(str(e))

    def _get_response_details(self) -> models.SessionDetails:
        return EmptyModel()

    @property
    def command_executor(self) -> CommandExecutor:
        return self

    @property
    def command_queue(self) -> CommandQueue:
        raise UnsupportedFeature()

    @property
    def session_type(self) -> models.SessionType:
        return models.SessionType.protocol

    async def execute(self, command: Command) -> CompletedCommand:
        """Execute protocol commands"""
        handler = self._handlers.get(command.content.name)
        if not handler:
            raise UnsupportedCommandException(
                f"Command '{command.content.name}' is not supported."
            )

        with duration() as timed:
            await handler(command)

        return CompletedCommand(
            content=command.content,
            meta=command.meta,
            result=CommandResult(started_at=timed.start,
                                 completed_at=timed.end)
        )

    async def handle_run(self, command: Command):
        self._th = Thread(
            target=runner,
            args=(self._uploaded_protocol,
                  self._configuration.hardware,
                  self._configuration.motion_lock,
                  Queue()
                  ))
        self._th.start()

    async def handle_simulate(self, command: Command):
        pass

    async def handle_cancel(self, command: Command):
        pass

    async def handle_pause(self, command: Command):
        pass

    async def handle_resume(self, command: Command):
        pass


def runner(protocol: UploadedProtocol,
           hardware: ThreadManager,
           motion_lock: ThreadedAsyncLock,
           queue: Queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    broker = Broker()
    notifications = Notifications(Session.TOPIC,
                                  broker,
                                  loop)

    async def _m():
        async for event in notifications:
            log.info(event)
            queue.put(event)

    task = loop.create_task(_m())

    c = os.getcwd()
    # Change working directory to temp dir
    os.chdir(protocol.meta.directory.name)
    # Add temp dir to path
    sys.path.append(protocol.meta.directory.name)

    try:
        session = Session.build_and_prep(
            protocol.meta.name,
            protocol.get_contents(),
            hardware,
            loop,
            broker,
            motion_lock,
            {}
        )
    except Exception:
        pass
    finally:
        task.cancel()
        loop.stop()
        # Undo working directory and path modifications
        os.chdir(c)
        sys.path.remove(protocol.meta.directory.name)
