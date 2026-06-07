from __future__ import annotations

import asyncio
import socket
import ssl
from dataclasses import dataclass

from deskaone_sdk.network.handlers.http import http_handler_conn
from deskaone_sdk.network.handlers.socks4 import socks4_handler_conn
from deskaone_sdk.network.handlers.socks5 import socks5_handler_conn
from deskaone_sdk.network.tcp_connection import TcpConnection
from deskaone_sdk.proxy.proxy_config import ProxyConfig
from deskaone_sdk.proxy.proxy_picker import ProxyPicker
from deskaone_sdk.proxy.proxy_type import ProxyType


class TcpClientError(Exception):
    pass


@dataclass(slots=True)
class TcpClientOptions:
    timeout: float = 30.0
    proxy_config: ProxyConfig | None = None
    proxy_picker: ProxyPicker | None = None
    local_addr: tuple[str, int] | None = None
    secure: bool = False
    server_name: str | None = None
    ssl_context: ssl.SSLContext | None = None
    verify_ssl: bool = True


class TCPClient:
    def __init__(
        self,
        *,
        timeout: float = 30.0,
        proxy_config: ProxyConfig | None = None,
        proxy_picker: ProxyPicker | None = None,
        local_addr: tuple[str, int] | None = None,
        secure: bool = False,
        server_name: str | None = None,
        ssl_context: ssl.SSLContext | None = None,
        verify_ssl: bool = True,
    ):
        self.options = TcpClientOptions(
            timeout=timeout,
            proxy_config=proxy_config,
            proxy_picker=proxy_picker,
            local_addr=local_addr,
            secure=secure,
            server_name=server_name,
            ssl_context=ssl_context,
            verify_ssl=verify_ssl,
        )

    async def connect(self, host: str, port: int) -> TcpConnection:
        if not host:
            raise TcpClientError("host must not be empty")
        if not 1 <= int(port) <= 65535:
            raise TcpClientError("port must be between 1 and 65535")
        proxy = self.options.proxy_config or (
            self.options.proxy_picker.pick() if self.options.proxy_picker else None
        )
        if proxy is None:
            return await self._connect_direct(host, port)
        return await self._connect_proxy(proxy, host, port)

    async def _connect_direct(self, host: str, port: int) -> TcpConnection:
        context = self._ssl_context() if self.options.secure else None
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                host,
                port,
                local_addr=self.options.local_addr,
                ssl=context,
                server_hostname=self.options.server_name or host if context else None,
            ),
            self.options.timeout,
        )
        self._set_tcp_nodelay(writer)
        return TcpConnection(reader, writer, is_secure=self.options.secure)

    async def _connect_proxy(self, proxy: ProxyConfig, host: str, port: int) -> TcpConnection:
        conn: TcpConnection | None = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(proxy.host, proxy.port, local_addr=self.options.local_addr),
                self.options.timeout,
            )
            self._set_tcp_nodelay(writer)
            conn = TcpConnection(reader, writer)
            if proxy.type == ProxyType.HTTP:
                await http_handler_conn(conn, proxy, host, port, self.options.timeout)
            elif proxy.type == ProxyType.SOCKS4:
                await socks4_handler_conn(conn, proxy, host, port, self.options.timeout)
            elif proxy.type == ProxyType.SOCKS5:
                await socks5_handler_conn(conn, proxy, host, port, self.options.timeout)
            else:
                raise TcpClientError(f"unsupported proxy type: {proxy.type}")
            if self.options.secure:
                await self._upgrade_tls(conn, host)
            return conn
        except Exception as exc:
            if conn is not None:
                conn.destroy()
            if isinstance(exc, TcpClientError):
                raise
            raise TcpClientError(str(exc)) from exc

    async def _upgrade_tls(self, conn: TcpConnection, host: str) -> None:
        context = self._ssl_context()
        try:
            await asyncio.wait_for(
                conn.writer.start_tls(context, server_hostname=self.options.server_name or host),
                self.options.timeout,
            )
            conn._is_secure = True  # noqa: SLF001
        except AttributeError as exc:
            raise TcpClientError(
                "TLS upgrade through proxy requires Python StreamWriter.start_tls"
            ) from exc

    def _ssl_context(self) -> ssl.SSLContext:
        if self.options.ssl_context is not None:
            return self.options.ssl_context
        if self.options.verify_ssl:
            return ssl.create_default_context()
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    @staticmethod
    def _set_tcp_nodelay(writer: asyncio.StreamWriter) -> None:
        sock = writer.get_extra_info("socket")
        if sock is not None:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
