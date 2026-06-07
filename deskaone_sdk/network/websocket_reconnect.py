from __future__ import annotations

import asyncio
import inspect
from typing import Any, Awaitable, Callable

from deskaone_sdk.network.websocket_client import WebSocketClient, WebSocketMessage

Callback = Callable[..., Awaitable[None] | None]


class ReconnectWebSocketClient:
    def __init__(
        self,
        uri: str,
        *,
        reconnect_delay: float = 2.0,
        max_reconnects: int = -1,
        on_connect: Callable[[WebSocketClient], Awaitable[None] | None] | None = None,
        on_message: Callable[[WebSocketMessage], Awaitable[None] | None] | None = None,
        on_error: Callable[[BaseException], Awaitable[None] | None] | None = None,
        on_disconnect: Callable[[BaseException | None], Awaitable[None] | None] | None = None,
        **websocket_options: Any,
    ):
        self.uri = uri
        self.websocket_options = websocket_options
        self.reconnect_delay = reconnect_delay
        self.max_reconnects = max_reconnects
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_error = on_error
        self.on_disconnect = on_disconnect
        self._current: WebSocketClient | None = None
        self._running = False
        self._manual_stop = False

    @property
    def current(self) -> WebSocketClient | None:
        return self._current

    @property
    def is_running(self) -> bool:
        return self._running

    async def run(self) -> None:
        self._running = True
        self._manual_stop = False
        reconnects = 0
        while self._running:
            error: BaseException | None = None
            try:
                self._current = await WebSocketClient.connect(self.uri, **self.websocket_options)
                reconnects = 0
                await _maybe_await(self.on_connect, self._current)
                async for message in self._current:
                    await _maybe_await(self.on_message, message)
            except Exception as exc:  # noqa: BLE001 - callback should see all errors
                error = exc
                await _maybe_await(self.on_error, exc)
            finally:
                await _maybe_await(self.on_disconnect, error)
                self._current = None
            if self._manual_stop or not self._running:
                break
            reconnects += 1
            if self.max_reconnects >= 0 and reconnects > self.max_reconnects:
                break
            await asyncio.sleep(self.reconnect_delay)
        self._running = False

    async def stop(self) -> None:
        self._manual_stop = True
        self._running = False
        if self._current:
            await self._current.close()

    async def close(self) -> None:
        await self.stop()

    async def send_text(self, text: str) -> None:
        if not self._current:
            raise RuntimeError("WebSocket is not connected")
        await self._current.send_text(text)

    async def send_json(self, value: Any) -> None:
        if not self._current:
            raise RuntimeError("WebSocket is not connected")
        await self._current.send_json(value)

    async def send_binary(self, data: bytes) -> None:
        if not self._current:
            raise RuntimeError("WebSocket is not connected")
        await self._current.send_binary(data)


async def _maybe_await(callback: Callback | None, *args: Any) -> None:
    if callback is None:
        return
    result = callback(*args)
    if inspect.isawaitable(result):
        await result
