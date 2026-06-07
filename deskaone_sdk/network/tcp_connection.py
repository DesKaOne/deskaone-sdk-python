from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque

BytesLike = bytes | bytearray | memoryview | str


class TcpConnection:
    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, *, is_secure: bool = False
    ):
        self._reader = reader
        self._writer = writer
        self._is_secure = is_secure
        self._leftover = bytearray()

    @property
    def reader(self) -> asyncio.StreamReader:
        return self._reader

    @property
    def writer(self) -> asyncio.StreamWriter:
        return self._writer

    @property
    def is_secure(self) -> bool:
        return self._is_secure

    @property
    def remote_address(self):
        return self._writer.get_extra_info("peername")

    @property
    def local_address(self):
        return self._writer.get_extra_info("sockname")

    async def write(self, data: BytesLike) -> None:
        if isinstance(data, str):
            raw = data.encode()
        else:
            raw = bytes(data)
        self._writer.write(raw)
        await self.drain()

    async def drain(self) -> None:
        await self._writer.drain()

    async def close(self) -> None:
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except (BrokenPipeError, ConnectionError, RuntimeError):
            pass

    def destroy(self) -> None:
        transport = self._writer.transport
        transport.abort()

    def push_leftover(self, data: bytes) -> None:
        if data:
            self._leftover = bytearray(data) + self._leftover

    async def read_exact(self, length: int, timeout: float | None = None) -> bytes:
        if length < 0:
            raise ValueError("length must be non-negative")
        out = bytearray()
        if self._leftover:
            take = min(length, len(self._leftover))
            out += self._leftover[:take]
            del self._leftover[:take]
        remaining = length - len(out)
        if remaining:
            out += await _wait(self._reader.readexactly(remaining), timeout)
        return bytes(out)

    async def read_some(self, max_bytes: int = 65536, timeout: float | None = None) -> bytes:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if self._leftover:
            take = min(max_bytes, len(self._leftover))
            data = bytes(self._leftover[:take])
            del self._leftover[:take]
            return data
        return await _wait(self._reader.read(max_bytes), timeout)

    async def read_until(
        self, delimiter: bytes, max_size: int, timeout: float | None = None
    ) -> tuple[bytes, bytes]:
        if not delimiter:
            raise ValueError("delimiter must not be empty")
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        chunks: Deque[bytes] = deque()
        size = 0
        while True:
            if self._leftover:
                chunk = bytes(self._leftover)
                self._leftover.clear()
            else:
                chunk = await _wait(self._reader.read(4096), timeout)
                if not chunk:
                    raise asyncio.IncompleteReadError(b"".join(chunks), None)
            chunks.append(chunk)
            size += len(chunk)
            data = b"".join(chunks)
            index = data.find(delimiter)
            if index >= 0:
                end = index + len(delimiter)
                head = data[:end]
                leftover = data[end:]
                if leftover:
                    self.push_leftover(leftover)
                return head, leftover
            if size > max_size:
                raise ValueError("read_until maximum size exceeded")


async def _wait(awaitable, timeout: float | None):
    if timeout is None:
        return await awaitable
    return await asyncio.wait_for(awaitable, timeout)
