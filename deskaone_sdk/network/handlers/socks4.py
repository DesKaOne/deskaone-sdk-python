from __future__ import annotations

import ipaddress
import struct

from deskaone_sdk.network.tcp_connection import TcpConnection
from deskaone_sdk.proxy.proxy_config import ProxyConfig


def socks4_reply_error(code: int) -> str:
    return {
        0x5B: "request rejected or failed",
        0x5C: "request failed because client is not running identd",
        0x5D: "request failed because client identd could not confirm userid",
    }.get(code, f"unknown SOCKS4 reply code 0x{code:02x}")


async def socks4_handler_conn(
    conn: TcpConnection,
    proxy_config: ProxyConfig,
    host: str,
    port: int,
    timeout: float | None = None,
) -> None:
    if "\x00" in host or (proxy_config.username and "\x00" in proxy_config.username):
        raise ValueError("SOCKS4 host/userid must not contain null bytes")
    userid = (proxy_config.username or "").encode()
    try:
        ip_bytes = ipaddress.IPv4Address(host).packed
        domain = b""
    except ipaddress.AddressValueError:
        ip_bytes = b"\x00\x00\x00\x01"
        domain = host.encode() + b"\x00"
    request = b"\x04\x01" + struct.pack("!H", port) + ip_bytes + userid + b"\x00" + domain
    await conn.write(request)
    reply = await conn.read_exact(8, timeout)
    if reply[0] != 0x00:
        raise RuntimeError(f"invalid SOCKS4 reply version 0x{reply[0]:02x}")
    if reply[1] != 0x5A:
        raise RuntimeError(f"SOCKS4 CONNECT failed: {socks4_reply_error(reply[1])}")
