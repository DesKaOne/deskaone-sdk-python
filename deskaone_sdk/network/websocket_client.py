from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import struct
from dataclasses import dataclass
from enum import IntEnum, Enum
from typing import Any
from urllib.parse import urlparse

from deskaone_sdk.network.tcp_client import TCPClient
from deskaone_sdk.proxy.proxy_config import ProxyConfig
from deskaone_sdk.proxy.proxy_picker import ProxyPicker

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketReadyState(str, Enum):
    CONNECTING = "connecting"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"


class WebSocketOpcode(IntEnum):
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


@dataclass(slots=True)
class WebSocketMessage:
    opcode: WebSocketOpcode
    data: bytes

    @property
    def text(self) -> str:
        return self.data.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.text)


class WebSocketClientError(Exception):
    pass


class WebSocketClient:
    def __init__(
        self,
        conn,
        uri: str,
        *,
        protocol: str | None = None,
        auto_pong: bool = True,
        max_payload_size: int = 16 * 1024 * 1024,
        ping_interval: float | None = None,
    ):
        self._conn = conn
        self._uri = uri
        self._protocol = protocol
        self._auto_pong = auto_pong
        self._max_payload_size = max_payload_size
        self._ping_interval = ping_interval
        self._ready_state = WebSocketReadyState.OPEN
        self._queue: asyncio.Queue[WebSocketMessage | None] = asyncio.Queue()
        self._closed = asyncio.Event()
        self._close_code: int | None = None
        self._close_reason: str | None = None
        self._reader_task = asyncio.create_task(self._reader_loop())
        self._ping_task = asyncio.create_task(self._ping_loop()) if ping_interval else None

    @classmethod
    async def connect(
        cls,
        uri: str,
        *,
        timeout: float = 30.0,
        proxy_config: ProxyConfig | None = None,
        proxy_picker: ProxyPicker | None = None,
        local_addr: tuple[str, int] | None = None,
        ssl_context=None,
        verify_ssl: bool = True,
        headers: dict[str, str] | None = None,
        subprotocols: list[str] | None = None,
        auto_pong: bool = True,
        max_payload_size: int = 16 * 1024 * 1024,
        ping_interval: float | None = None,
    ) -> WebSocketClient:
        parsed = urlparse(uri)
        if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
            raise WebSocketClientError("URI must be ws(s) and include a host")
        secure = parsed.scheme == "wss"
        port = parsed.port or (443 if secure else 80)
        client = TCPClient(
            timeout=timeout,
            proxy_config=proxy_config,
            proxy_picker=proxy_picker,
            local_addr=local_addr,
            secure=secure,
            ssl_context=ssl_context,
            verify_ssl=verify_ssl,
        )
        conn = await client.connect(parsed.hostname, port)
        try:
            key = base64.b64encode(secrets.token_bytes(16)).decode()
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"
            host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
            if parsed.port:
                host = f"{host}:{parsed.port}"
            request_headers = {
                "Host": host,
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": key,
                "Sec-WebSocket-Version": "13",
                "User-Agent": "DesKaOnePython/0.1.0",
                **(headers or {}),
            }
            if subprotocols:
                request_headers["Sec-WebSocket-Protocol"] = ", ".join(subprotocols)
            lines = [
                f"GET {path} HTTP/1.1",
                *(f"{k}: {v}" for k, v in request_headers.items()),
                "",
                "",
            ]
            await conn.write("\r\n".join(lines))
            raw_headers, _ = await conn.read_until(b"\r\n\r\n", 32 * 1024, timeout)
            status, response_headers = parse_handshake_response(raw_headers)
            if status != 101:
                raise WebSocketClientError(f"WebSocket upgrade failed with status {status}")
            expected = websocket_accept(key)
            if response_headers.get("sec-websocket-accept", [None])[-1] != expected:
                raise WebSocketClientError("invalid Sec-WebSocket-Accept")
            protocol = response_headers.get("sec-websocket-protocol", [None])[-1]
            return cls(
                conn,
                uri,
                protocol=protocol,
                auto_pong=auto_pong,
                max_payload_size=max_payload_size,
                ping_interval=ping_interval,
            )
        except Exception:
            conn.destroy()
            raise

    @property
    def ready_state(self) -> WebSocketReadyState:
        return self._ready_state

    @property
    def protocol(self) -> str | None:
        return self._protocol

    @property
    def close_code(self) -> int | None:
        return self._close_code

    @property
    def close_reason(self) -> str | None:
        return self._close_reason

    async def send_text(self, text: str) -> None:
        await self._send_frame(WebSocketOpcode.TEXT, text.encode())

    async def send_json(self, value: Any) -> None:
        await self.send_text(json.dumps(value))

    async def send_binary(self, data: bytes) -> None:
        await self._send_frame(WebSocketOpcode.BINARY, data)

    async def ping(self, payload: bytes = b"") -> None:
        await self._send_frame(WebSocketOpcode.PING, payload)

    async def pong(self, payload: bytes = b"") -> None:
        await self._send_frame(WebSocketOpcode.PONG, payload)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        if self._ready_state in {WebSocketReadyState.CLOSING, WebSocketReadyState.CLOSED}:
            return
        self._ready_state = WebSocketReadyState.CLOSING
        await self._send_frame(WebSocketOpcode.CLOSE, encode_close_payload(code, reason))
        await self.wait_closed()

    def destroy(self) -> None:
        self._ready_state = WebSocketReadyState.CLOSED
        self._conn.destroy()
        if self._reader_task:
            self._reader_task.cancel()
        if self._ping_task:
            self._ping_task.cancel()
        self._closed.set()

    async def wait_closed(self) -> None:
        await self._closed.wait()

    async def recv(self) -> WebSocketMessage:
        item = await self._queue.get()
        if item is None:
            raise WebSocketClientError("WebSocket is closed")
        return item

    def __aiter__(self):
        return self

    async def __anext__(self) -> WebSocketMessage:
        try:
            return await self.recv()
        except WebSocketClientError as exc:
            raise StopAsyncIteration from exc

    async def _send_frame(self, opcode: WebSocketOpcode, payload: bytes) -> None:
        if self._ready_state == WebSocketReadyState.CLOSED:
            raise WebSocketClientError("WebSocket is closed")
        if (
            opcode in {WebSocketOpcode.PING, WebSocketOpcode.PONG, WebSocketOpcode.CLOSE}
            and len(payload) > 125
        ):
            raise WebSocketClientError("control frame payload too large")
        await self._conn.write(encode_frame(opcode, payload, mask=True))

    async def _reader_loop(self) -> None:
        current_opcode: WebSocketOpcode | None = None
        fragments = bytearray()
        try:
            while True:
                frame = await read_frame(self._conn, self._max_payload_size)
                opcode, payload, fin = frame
                if opcode == WebSocketOpcode.PING:
                    if self._auto_pong:
                        await self.pong(payload)
                    await self._queue.put(WebSocketMessage(opcode, payload))
                elif opcode == WebSocketOpcode.PONG:
                    await self._queue.put(WebSocketMessage(opcode, payload))
                elif opcode == WebSocketOpcode.CLOSE:
                    self._close_code, self._close_reason = decode_close_payload(payload)
                    if self._ready_state == WebSocketReadyState.OPEN:
                        await self._send_frame(WebSocketOpcode.CLOSE, payload)
                    break
                elif opcode in {WebSocketOpcode.TEXT, WebSocketOpcode.BINARY}:
                    if fin:
                        await self._queue.put(WebSocketMessage(opcode, payload))
                    else:
                        current_opcode = opcode
                        fragments = bytearray(payload)
                elif opcode == WebSocketOpcode.CONTINUATION:
                    if current_opcode is None:
                        raise WebSocketClientError("unexpected continuation frame")
                    fragments += payload
                    if len(fragments) > self._max_payload_size:
                        raise WebSocketClientError("WebSocket payload too large")
                    if fin:
                        await self._queue.put(WebSocketMessage(current_opcode, bytes(fragments)))
                        current_opcode = None
                        fragments.clear()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            self._ready_state = WebSocketReadyState.CLOSED
            if self._ping_task:
                self._ping_task.cancel()
            await self._conn.close()
            await self._queue.put(None)
            self._closed.set()

    async def _ping_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._ping_interval or 0)
                await self.ping()
        except asyncio.CancelledError:
            pass


def websocket_accept(key: str) -> str:
    digest = hashlib.sha1((key + WS_GUID).encode()).digest()
    return base64.b64encode(digest).decode()


def parse_handshake_response(data: bytes) -> tuple[int, dict[str, list[str]]]:
    lines = data.decode("iso-8859-1", "replace").split("\r\n")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise WebSocketClientError("invalid WebSocket handshake response")
    headers: dict[str, list[str]] = {}
    for line in lines[1:]:
        if not line:
            continue
        key, value = line.split(":", 1)
        headers.setdefault(key.lower(), []).append(value.strip())
    return int(parts[1]), headers


def encode_frame(opcode: WebSocketOpcode, payload: bytes, *, mask: bool, fin: bool = True) -> bytes:
    first = (0x80 if fin else 0) | int(opcode)
    length = len(payload)
    if length < 126:
        header = bytes([first, (0x80 if mask else 0) | length])
    elif length <= 0xFFFF:
        header = bytes([first, (0x80 if mask else 0) | 126]) + struct.pack("!H", length)
    else:
        header = bytes([first, (0x80 if mask else 0) | 127]) + struct.pack("!Q", length)
    if not mask:
        return header + payload
    key = secrets.token_bytes(4)
    return header + key + mask_payload(payload, key)


def mask_payload(payload: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[index % 4] for index, byte in enumerate(payload))


async def read_frame(conn, max_payload_size: int) -> tuple[WebSocketOpcode, bytes, bool]:
    first_two = await conn.read_exact(2)
    first, second = first_two
    fin = bool(first & 0x80)
    if first & 0x70:
        raise WebSocketClientError("RSV bits are not supported")
    opcode = WebSocketOpcode(first & 0x0F)
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", await conn.read_exact(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", await conn.read_exact(8))[0]
    if length > max_payload_size:
        raise WebSocketClientError("WebSocket payload too large")
    if opcode in {WebSocketOpcode.CLOSE, WebSocketOpcode.PING, WebSocketOpcode.PONG}:
        if not fin or length > 125:
            raise WebSocketClientError("invalid fragmented/large control frame")
    key = await conn.read_exact(4) if masked else b""
    payload = await conn.read_exact(length) if length else b""
    if masked:
        payload = mask_payload(payload, key)
    return opcode, payload, fin


def encode_close_payload(code: int = 1000, reason: str = "") -> bytes:
    return struct.pack("!H", code) + reason.encode()


def decode_close_payload(payload: bytes) -> tuple[int | None, str]:
    if not payload:
        return None, ""
    if len(payload) == 1:
        raise WebSocketClientError("invalid close payload")
    return struct.unpack("!H", payload[:2])[0], payload[2:].decode("utf-8", "replace")
