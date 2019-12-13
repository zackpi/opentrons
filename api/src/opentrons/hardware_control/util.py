""" Utility functions and classes for the hardware controller"""
import functools
import asyncio
from typing import Callable

from . import types, adapters, API, HardwareAPILike


class PauseManager():
    """ This centralizes the runtime control of hardware that allows
    atomic actions to be "paused" and subsequently "resumed"
    """

    def __init__(self,
                 loop: asyncio.AbstractEventLoop = None,
                 is_simulating: bool) -> None:
        if None is loop:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop
        self._is_running_flag = asyncio.Event(self._loop)
        self._is_simulating = is_simulating

    async def pausable(self, decorated_obj: Callable) -> Callable:
        """ Decorator. Apply to Hardware Control methods or attributes to indicate
        they should be held and released by pauses and resumes respectively.
        """
        @functools.wraps(decorated_obj)
        async def _hold_if_paused(*args, **kwargs):
            if not self._is_simulating:
                await self._is_running_flag.wait()
            return decorated_obj(*args, **kwargs)

      return _hold_if_paused

    def pause(self):
        self._is_running_flag.clear()

    def resume(self):
        self._is_running_flag.set()

