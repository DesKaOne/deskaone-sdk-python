from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any


class Debouncer:
    def __init__(self, delay: float, action: Callable[[], Any]):
        self.delay = delay
        self.action = action
        self._task: asyncio.Task[None] | None = None
        self._disposed = False

    def call(self) -> None:
        if self._disposed:
            return
        self.cancel()
        self._task = asyncio.create_task(self._run())

    def cancel(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    def dispose(self) -> None:
        self._disposed = True
        self.cancel()

    async def _run(self) -> None:
        try:
            await asyncio.sleep(self.delay)
            result = self.action()
            if inspect.isawaitable(result):
                await result
        except asyncio.CancelledError:
            pass
