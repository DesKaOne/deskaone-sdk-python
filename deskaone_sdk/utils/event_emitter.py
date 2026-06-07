from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _Listener:
    id: int
    handler: Callable[..., Any]
    once: bool = False


class EventEmitter:
    def __init__(self):
        self._listeners: dict[Any, list[_Listener]] = defaultdict(list)
        self._next_id = 1

    def on(self, event: Any, handler: Callable[..., Any]) -> int:
        return self._add(event, handler, False)

    def once(self, event: Any, handler: Callable[..., Any]) -> int:
        return self._add(event, handler, True)

    def off(self, event: Any, id: int) -> None:  # noqa: A002
        self._listeners[event] = [item for item in self._listeners[event] if item.id != id]

    def emit(self, event: Any, *args: Any, **kwargs: Any) -> None:
        snapshot = list(self._listeners[event])
        for listener in snapshot:
            listener.handler(*args, **kwargs)
            if listener.once:
                self.off(event, listener.id)

    async def emit_async(self, event: Any, *args: Any, **kwargs: Any) -> None:
        snapshot = list(self._listeners[event])
        for listener in snapshot:
            result = listener.handler(*args, **kwargs)
            if inspect.isawaitable(result):
                await result
            if listener.once:
                self.off(event, listener.id)

    def clear(self, event: Any | None = None) -> None:
        if event is None:
            self._listeners.clear()
        else:
            self._listeners.pop(event, None)

    def listener_count(self, event: Any) -> int:
        return len(self._listeners[event])

    def _add(self, event: Any, handler: Callable[..., Any], once: bool) -> int:
        listener_id = self._next_id
        self._next_id += 1
        self._listeners[event].append(_Listener(listener_id, handler, once))
        return listener_id
