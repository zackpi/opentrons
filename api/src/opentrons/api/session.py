import asyncio
import base64
from copy import copy
from functools import reduce
import logging
from time import time, sleep
from typing import List, Dict, Any, Optional, Set, TYPE_CHECKING
from uuid import uuid4

from opentrons.api.util import (RobotBusy, robot_is_busy,
                                requires_http_protocols_disabled)
from opentrons.drivers.smoothie_drivers.driver_3_0 import SmoothieAlarm
from opentrons.drivers.rpi_drivers.gpio_simulator import SimulatingGPIOCharDev
from opentrons import robot
from opentrons.broker import Broker
from opentrons.config import feature_flags as ff
from opentrons.commands import tree, types as command_types
from opentrons.commands.commands import is_new_loc, listify
from opentrons.protocols.implementations.protocol_context import \
    ProtocolContextImplementation
from opentrons.protocols.types import PythonProtocol, APIVersion
from opentrons.protocols.parse import parse
from opentrons.types import Location, Point
from opentrons.calibration_storage import helpers
from opentrons.protocol_api import (ProtocolContext,
                                    labware)
from opentrons.protocols.geometry import module_geometry
from opentrons.protocols.execution.execute import run_protocol
from opentrons.hardware_control import (API, ThreadManager,
                                        ExecutionCancelledError,
                                        ThreadedAsyncLock)
from opentrons.hardware_control.types import (DoorState, HardwareEventType,
                                              HardwareEvent)
from .models import Container, Instrument, Module

from opentrons.legacy_api.containers.placeable import (
    Module as ModulePlaceable, Placeable)

from opentrons.legacy_api.containers import get_container, location_to_list

if TYPE_CHECKING:
    from .dev_types import State, StateInfo

log = logging.getLogger(__name__)

VALID_STATES: Set['State'] = {
    'loaded', 'running', 'finished', 'stopped', 'paused', 'error'}


class SessionManager:
    def __init__(
            self, hardware, loop=None, broker=None, lock=None):
        self._broker = broker or Broker()
        self._loop = loop or asyncio.get_event_loop()
        self.session = None
        self._session_lock = False
        self._hardware = hardware
        self._command_logger = logging.getLogger(
            'opentrons.server.command_logger')
        self._broker.set_logger(self._command_logger)
        self._motion_lock = lock

    @requires_http_protocols_disabled
    def create(
            self,
            name: str,
            contents: str,
            is_binary: bool = False) -> 'Session':
        """ Create a protocol session from either

        - a json protocol
        - a python protocol file
        - a zipped protocol bundle (deprecated, for back compat)

        No new code should be written that calls this function with
        ``is_binary=True`` and a base64'd zip in ``contents``; instead,
        use :py:meth:`.create_from_bundle`.

        :param str name: The name of the protocol
        :param str contents: The contents of the protocol; this should be
                             either the contents of the file if it can be
                             parsed directly or a base64d version of the
                             contents if it is a zip. If it is base64,
                             ``is_binary`` must be true. Do not write new
                             code that uses this.
        :param bool is_binary: ``True`` if ``contents`` is a base64'd zip.
                               Do not write new code that uses this.
        :returns Session: The created session.
        :raises Exception: If another session is simulating at the time

        .. note::

            This function is mostly (only) intended to be called via rpc.
        """
        if is_binary:
            log.warning("session.create: called with bundle")

        if self._session_lock:
            raise Exception(
                'Cannot create session while simulation in progress')

        self.clear()
        self._session_lock = True
        try:
            _contents = base64.b64decode(contents) if is_binary else contents
            session_short_id = hex(uuid4().fields[0])
            session_logger = self._command_logger.getChild(session_short_id)
            self._broker.set_logger(session_logger)
            self.session = Session.build_and_prep(
                name=name,
                contents=_contents,
                hardware=self._hardware,
                loop=self._loop,
                broker=self._broker,
                motion_lock=self._motion_lock,
                extra_labware=[])
            return self.session
        finally:
            self._session_lock = False

    @requires_http_protocols_disabled
    def create_from_bundle(self, name: str, contents: str) -> 'Session':
        """ Create a protocol session from a base64'd zip file.

        :param str name: The name of the protocol
        :param str contents: The contents of the zip file, base64
                             encoded
        :returns Session: The created session
        :raises Exception: If another session is simulating at the time

        .. note::

            This function is mostly (only) intended to be called via rpc.
        """
        if self._session_lock:
            raise Exception(
                'Cannot create session while simulation in progress')

        self.clear()
        self._session_lock = True
        try:
            _contents = base64.b64decode(contents)
            session_short_id = hex(uuid4().fields[0])
            session_logger = self._command_logger.getChild(session_short_id)
            self._broker.set_logger(session_logger)
            self.session = Session.build_and_prep(
                name=name,
                contents=_contents,
                hardware=self._hardware,
                loop=self._loop,
                broker=self._broker,
                motion_lock=self._motion_lock,
                extra_labware=[])
            return self.session
        finally:
            self._session_lock = False

    @requires_http_protocols_disabled
    def create_with_extra_labware(
            self,
            name: str,
            contents: str,
            extra_labware: List[Dict[str, Any]]) -> 'Session':
        """
        Create a protocol session from a python protocol string with a list
        of extra custom labware to make available.

        :param str name: The name of the protocol
        :param str contents: The contents of the protocol file
        :param extra_labware: A list of labware definitions to make available
                              to protocol executions. This should be a list
                              of directly serialized definitions.
        :returns Session: The created session
        :raises Exception: If another session is simulating at the time

        .. note::

            This function is mostly (only) intended to be called via rpc.
        """
        if self._session_lock:
            raise Exception(
                "Cannot create session while simulation in progress")

        self.clear()
        self._session_lock = True
        try:
            session_short_id = hex(uuid4().fields[0])
            session_logger = self._command_logger.getChild(session_short_id)
            self._broker.set_logger(session_logger)
            self.session = Session.build_and_prep(
                name=name,
                contents=contents,
                hardware=self._hardware,
                loop=self._loop,
                broker=self._broker,
                motion_lock=self._motion_lock,
                extra_labware=extra_labware)
            return self.session
        finally:
            self._session_lock = False

    def clear(self):
        if self._session_lock:
            raise Exception(
                'Cannot clear session while simulation in progress')

        if self.session:
            self.session._remove_hardware_event_watcher()
            self._hardware.reset()
        self.session = None
        self._broker.set_logger(self._command_logger)

    def get_session(self):
        return self.session


class Session(RobotBusy):
    TOPIC = 'session'

    @classmethod
    def build_and_prep(
        cls, name, contents, hardware, loop, broker, motion_lock, extra_labware
    ):
        protocol = parse(contents, filename=name,
                         extra_labware={helpers.uri_from_definition(defn): defn
                                        for defn in extra_labware})
        sess = cls(name, protocol, hardware, loop, broker, motion_lock)
        sess.prepare()
        return sess

    def __init__(self, name, protocol, hardware, loop, broker, motion_lock):
        self._broker = broker
        self._default_logger = self._broker.logger
        self._sim_logger = self._broker.logger.getChild('sim')
        self._run_logger = self._broker.logger.getChild('run')
        self._loop = loop
        self.name = name
        self._protocol = protocol
        self.api_level = getattr(self._protocol, 'api_level', APIVersion(2, 0))
        self._use_v2 = self.api_level >= APIVersion(2, 0)
        log.info(
            f'Protocol API Version: {self.api_level}; '
            f'Protocol kind: {type(self._protocol)}')

        # self.metadata is exposed via rpc
        self.metadata = getattr(self._protocol, 'metadata', {})

        self._hardware = hardware
        self._simulating_ctx = ProtocolContext(
            implementation=ProtocolContextImplementation.build_using(
                self._protocol, loop=self._loop, broker=self._broker)
        )

        self.state: 'State' = None
        #: The current state
        self.stateInfo: 'StateInfo' = {}
        #: A message associated with the current state
        self.commands = []
        self.command_log = {}
        self.errors = []

        self._containers = []
        self._instruments = []
        self._modules = []
        self._interactions = []

        self.instruments = None
        self.containers = None
        self.modules = None
        self.protocol_text = protocol.text

        self.startTime: Optional[float] = None
        self._motion_lock = motion_lock
        self._event_watcher = None
        self.door_state: Optional[str] = None
        self.blocked: Optional[bool] = None

    @property
    def busy_lock(self) -> ThreadedAsyncLock:
        return self._motion_lock

    def _hw_iface(self):
        if self._use_v2:
            return self._hardware
        else:
            return robot

    def prepare(self):
        if not self._use_v2:
            robot.discover_modules()

        self.refresh()

    def get_instruments(self):
        return [
            Instrument(
                instrument=instrument,
                containers=[
                    container
                    for _instrument, container in
                    self._interactions
                    if _instrument == instrument
                ],
                context=self._use_v2 and self._simulating_ctx)
            for instrument in self._instruments
        ]

    def get_containers(self):
        return [
            Container(
                container=container,
                instruments=[
                    instrument
                    for instrument, _container in
                    self._interactions
                    if _container == container
                ],
                context=self._use_v2 and self._simulating_ctx)
            for container in self._containers
        ]

    def get_modules(self):
        return [
            Module(module=module,
                   context=self._use_v2 and self._simulating_ctx)
            for module in self._modules
        ]

    def clear_logs(self):
        self.command_log.clear()
        self.errors.clear()

    @robot_is_busy
    def _simulate(self):
        self._reset()

        stack: List[Dict[str, Any]] = []
        res: List[Dict[str, Any]] = []
        commands: List[Dict[str, Any]] = []

        self._containers.clear()
        self._instruments.clear()
        self._modules.clear()
        self._interactions.clear()

        def on_command(message):
            payload = message['payload']
            description = payload.get('text', '').format(
                **payload
            )

            if message['$'] == 'before':
                level = len(stack)

                stack.append(message)
                commands.append(payload)

                res.append(
                    {
                        'level': level,
                        'description': description,
                        'id': len(res)})
            else:
                stack.pop()
        unsubscribe = self._broker.subscribe(command_types.COMMAND, on_command)
        old_robot_connect = robot.connect

        try:
            # ensure actual pipettes are cached before driver is disconnected
            self._hardware.cache_instruments()
            if self._use_v2:
                instrs = {}
                for mount, pip in self._hardware.attached_instruments.items():
                    if pip:
                        instrs[mount] = {'model': pip['model'],
                                         'id': pip.get('pipette_id', '')}
                sync_sim = ThreadManager(
                        API.build_hardware_simulator,
                        instrs,
                        [mod.name()
                            for mod in self._hardware.attached_modules],
                        strict_attached_instruments=False
                        ).sync
                sync_sim.home()
                ctx_impl = ProtocolContextImplementation.build_using(
                    self._protocol,
                    loop=self._loop,
                    hardware=sync_sim,
                    broker=self._broker,
                    extra_labware=getattr(self._protocol, 'extra_labware', {}))
                self._simulating_ctx = ProtocolContext(implementation=ctx_impl)
                run_protocol(self._protocol,
                             context=self._simulating_ctx)
            else:
                robot.broker = self._broker
                # we don't rely on being connected anymore so make sure we are
                robot.connect()
                robot._driver.gpio_chardev = SimulatingGPIOCharDev('sim_chip')
                robot.cache_instrument_models()
                robot.disconnect()

                def robot_connect_error(port=None, options=None):
                    raise RuntimeError(
                        'Protocols executed through the Opentrons App may not '
                        'use robot.connect(). Allowing this call would cause '
                        'the robot to execute commands during simulation, and '
                        'then raise an error on execution.')
                robot.connect = robot_connect_error  # type: ignore
                exec(self._protocol.contents, {})
        finally:
            # physically attached pipettes are re-cached during robot.connect()
            # which is important, because during a simulation, the robot could
            # think that it holds a pipette model that it actually does not
            if not self._use_v2:
                robot.connect = old_robot_connect  # type: ignore
                robot.connect()

            unsubscribe()

            instruments, containers, modules, interactions = _accumulate(
                [_get_labware(command) for command in commands])

            self._containers.extend(_dedupe(containers))
            self._instruments.extend(_dedupe(
                instruments
                + list(self._simulating_ctx.loaded_instruments.values())))
            self._modules.extend(_dedupe(
                modules
                + [m._geometry
                   for m in self._simulating_ctx.loaded_modules.values()]))
            self._interactions.extend(_dedupe(interactions))

            # Labware calibration happens after simulation and before run, so
            # we have to clear the tips if they are left on after simulation
            # to ensure that the instruments are in the expected state at the
            # beginning of the labware calibration flow
            if not self._use_v2:
                robot.clear_tips()

        return res

    def refresh(self):
        self._reset()

        try:
            self._broker.set_logger(self._sim_logger)
            commands = self._simulate()
        except Exception:
            raise
        finally:
            self._broker.set_logger(self._default_logger)

        self.commands = tree.from_list(commands)

        self.containers = self.get_containers()
        self.instruments = self.get_instruments()
        self.modules = self.get_modules()
        self.startTime = None
        self.set_state('loaded')

        return self

    def stop(self):
        self._hw_iface().halt()
        with self._motion_lock.lock():
            try:
                self._hw_iface().stop()
            except asyncio.CancelledError:
                pass
        self.set_state('stopped')
        return self

    def pause(self,
              reason: str = None,
              user_message: str = None,
              duration: float = None):
        if self._use_v2:
            self._hardware.pause()
        # robot.pause in the legacy API will publish commands to the broker
        # use the broker-less execute_pause instead
        else:
            robot.execute_pause()

        self.set_state(
            'paused', reason=reason,
            user_message=user_message, duration=duration)
        return self

    def resume(self):
        if not self.blocked:
            if self._use_v2:
                self._hardware.resume()
            # robot.resume in the legacy API will publish commands to the
            # broker use the broker-less execute_resume instead
            else:
                robot.execute_resume()

            self.set_state('running')
            return self

    def _start_hardware_event_watcher(self):
        if not callable(self._event_watcher):
            # initialize and update window switch state
            self._update_window_state(self._hardware.door_state)
            log.info('Starting hardware event watcher')
            self._event_watcher = self._hardware.register_callback(
                self._handle_hardware_event)
        else:
            log.warning("Cannot start new hardware event watcher "
                        "when one already exists")

    def _remove_hardware_event_watcher(self):
        if callable(self._event_watcher):
            self._event_watcher()
            self._event_watcher = None

    def _handle_hardware_event(self, hw_event: 'HardwareEvent'):
        if hw_event.event == HardwareEventType.DOOR_SWITCH_CHANGE:
            self._update_window_state(hw_event.new_state)
            if ff.enable_door_safety_switch() and \
                    hw_event.new_state == DoorState.OPEN and \
                    self.state == 'running':
                self.pause('Robot door is open')
            else:
                self._on_state_changed()

    def _update_window_state(self, state: DoorState):
        self.door_state = str(state)
        if ff.enable_door_safety_switch() and \
                state == DoorState.OPEN:
            self.blocked = True
        else:
            self.blocked = False

    @robot_is_busy  # noqa(C901)
    def _run(self):
        def on_command(message):
            if message['$'] == 'before':
                self.log_append()
            if message['name'] == command_types.PAUSE:
                self.set_state('paused',
                               reason='The protocol paused execution',
                               user_message=message['payload']['userMessage'])
            if message['name'] == command_types.RESUME:
                self.set_state('running')

        self._reset()

        _unsubscribe = self._broker.subscribe(
            command_types.COMMAND, on_command)

        self.startTime = now()
        self.set_state('running')

        try:
            if self._use_v2:
                self.resume()
                self._pre_run_hooks()
                self._hardware.cache_instruments()
                self._hardware.reset_instrument()
                ctx_impl = ProtocolContextImplementation.build_using(
                    self._protocol,
                    loop=self._loop,
                    broker=self._broker,
                    extra_labware=getattr(self._protocol, 'extra_labware', {}))
                ctx = ProtocolContext(implementation=ctx_impl)
                ctx.connect(self._hardware)
                ctx.home()
                run_protocol(self._protocol, context=ctx)
            else:
                robot.broker = self._broker
                assert isinstance(self._protocol, PythonProtocol),\
                    'Internal error: v1 should only be used for python'
                if not robot.is_connected():
                    robot.connect()
                # backcompat patch: gpiod can only be used from one place so
                # we have to give the instance of the smoothie driver used by
                # the apiv1 singletons a reference to the main gpio driver
                robot._driver.gpio_chardev\
                    = self._hardware._backend.gpio_chardev
                self.resume()
                self._pre_run_hooks()
                robot.cache_instrument_models()
                robot.discover_modules()
                exec(self._protocol.contents, {})

            # If the last command in a protocol was a pause, the protocol
            # will immediately finish executing because there's no smoothie
            # command to block... except the home that's about to happen,
            # which will confuse the app and lock it up. So we need to
            # do our own pause here, and sleep the thread until/unless the
            # app resumes us.
            #
            # Cancelling from the app during this pause will result in the
            # smoothie giving us an error during the subsequent home, which
            # is tragic but expected.
            while self.state == 'paused':
                sleep(0.1)
            self.set_state('finished')
            self._hw_iface().home()
        except (SmoothieAlarm, asyncio.CancelledError,
                ExecutionCancelledError):
            log.info("Protocol cancelled")
        except Exception as e:
            log.exception("Exception during run:")
            self.error_append(e)
            self.set_state('error')
            raise e
        finally:
            _unsubscribe()

    def run(self):
        if not self.blocked:
            try:
                self._broker.set_logger(self._run_logger)
                self._run()
            except Exception:
                raise
            finally:
                self._broker.set_logger(self._default_logger)
            return self
        else:
            raise RuntimeError(
                'Protocol is blocked and cannot run. Make sure robot door '
                'is closed before running.')

    def set_state(self, state: 'State',
                  reason: str = None,
                  user_message: str = None,
                  duration: float = None):
        if state not in VALID_STATES:
            raise ValueError(
                'Invalid state: {0}. Valid states are: {1}'
                .format(state, VALID_STATES))
        self.state = state
        if user_message:
            self.stateInfo['userMessage'] = user_message
        else:
            self.stateInfo.pop('userMessage', None)
        if reason:
            self.stateInfo['message'] = reason
        else:
            self.stateInfo.pop('message', None)
        if duration:
            self.stateInfo['estimatedDuration'] = duration
        else:
            self.stateInfo.pop('estimatedDuration', None)
        if self.startTime:
            self.stateInfo['changedAt'] = now()-self.startTime
        else:
            self.stateInfo.pop('changedAt', None)
        self._on_state_changed()

    def log_append(self):
        self.command_log.update({
            len(self.command_log): now()})
        self._on_state_changed()

    def error_append(self, error):
        self.errors.append(
            {
                'timestamp': now(),
                'error': error
            }
        )

    def _reset(self):
        self._hw_iface().reset()
        self.clear_logs()
        # unregister existing event watcher
        self._remove_hardware_event_watcher()
        self._start_hardware_event_watcher()

    def _snapshot(self):
        if self.state == 'loaded':
            payload: Any = copy(self)
        else:
            if self.command_log.keys():
                idx = sorted(self.command_log.keys())[-1]
                timestamp = self.command_log[idx]
                last_command: Optional[Dict[str, Any]]\
                    = {'id': idx, 'handledAt': timestamp}
            else:
                last_command = None

            payload = {
                'state': self.state,
                'stateInfo': self.stateInfo,
                'startTime': self.startTime,
                'doorState': self.door_state,
                'blocked': self.blocked,
                'errors': self.errors,
                'lastCommand': last_command
            }
        return {
            'topic': Session.TOPIC,
            'payload': payload
        }

    def _on_state_changed(self):
        snap = self._snapshot()
        self._broker.publish(Session.TOPIC, snap)

    def _pre_run_hooks(self):
        self._hw_iface().home_z()


def _accumulate(iterable):
    return reduce(
        lambda x, y: tuple([x + y for x, y in zip(x, y)]),  # type: ignore
        iterable,
        ([], [], [], []))


def _dedupe(iterable):
    acc = set()  # type: ignore

    for item in iterable:
        if item not in acc:
            acc.add(item)
            yield item


def now():
    return int(time() * 1000)


def _get_parent_module(placeable):
    if not placeable or isinstance(placeable, (Point, str)):
        res = None
    elif isinstance(placeable,
                    (ModulePlaceable, module_geometry.ModuleGeometry)):
        res = placeable
    elif isinstance(placeable, List):
        res = _get_parent_module(placeable[0].parent)
    else:
        res = _get_parent_module(placeable.parent)
    return res


def _get_new_labware(loc):
    if isinstance(loc, Location):
        return _get_new_labware(loc.labware)
    elif isinstance(loc, labware.Well):
        return loc.parent
    elif isinstance(loc, labware.Labware):
        return loc
    else:
        raise TypeError(loc)


def _get_labware(command):  # noqa(C901)
    containers = []
    instruments = []
    modules = []
    interactions = []

    location = command.get('location')
    instrument = command.get('instrument')

    placeable = location
    if isinstance(location, Location):
        placeable = location.labware.object
    elif isinstance(location, tuple):
        placeable = location[0]

    maybe_module = _get_parent_module(placeable)
    modules.append(maybe_module)

    locations = command.get('locations')
    multiple_instruments = command.get('instruments')

    if location:
        if isinstance(location, (Placeable)) or type(location) == tuple:
            # type()== used here instead of isinstance because a specific
            # named tuple like location descends from tuple and therefore
            # passes the check
            containers.append(get_container(location))
        elif isinstance(location, Location):
            if location.labware.is_well:
                containers.append(location.labware.parent.as_labware())
            elif location.labware.is_labware:
                containers.append(location.labware.as_labware())
        else:
            log.error(f'Cant handle location {location!r}')

    if locations:
        if is_new_loc(locations):
            list_of_locations = listify(locations)
            containers.extend(
                [_get_new_labware(loc) for loc in list_of_locations])
        else:
            list_of_locations = location_to_list(locations)
            containers.extend(
                [get_container(location) for location in list_of_locations])

    containers = [c for c in containers if c is not None]
    modules = [m for m in modules if m is not None]

    if instrument:
        instruments.append(instrument)
        interactions.extend(
            [(instrument, container) for container in containers])
    if multiple_instruments:
        for instr in multiple_instruments:
            instruments.append(instr)
            interactions.extend(
                [(instr, container) for container in containers])

    return instruments, containers, modules, interactions
