from __future__ import annotations

import struct

from deskaone_sdk.network.tcp_connection import TcpConnection
from deskaone_sdk.proxy.proxy_config import ProxyConfig


def socks5_reply_error(code: int) -> str:
    return {
        0x01: "general SOCKS server failure",
        0x02: "connection not allowed by ruleset",
        0x03: "network unreachable",
        0x04: "host unreachable",
        0x05: "connection refused",
        0x06: "TTL expired",
        0x07: "command not supported",
        0x08: "address type not supported",
    }.get(code, f"unknown SOCKS5 reply code 0x{code:02x}")


async def socks5_handler_conn(
    conn: TcpConnection,
    proxy_config: ProxyConfig,
    host: str,
    port: int,
    timeout: float | None = None,
) -> None:
    methods = [0x00]
    has_auth = proxy_config.username is not None
    if has_auth:
        methods.append(0x02)
    await conn.write(bytes([0x05, len(methods), *methods]))
    chosen = await conn.read_exact(2, timeout)
    if chosen[0] != 0x05:
        raise RuntimeError("invalid SOCKS5 method negotiation version")
    if chosen[1] == 0xFF:
        raise RuntimeError("SOCKS5 proxy offered no acceptable authentication methods")
    if chosen[1] == 0x02:
        username = (proxy_config.username or "").encode()
        password = (proxy_config.password or "").encode()
        if len(username) > 255 or len(password) > 255:
            raise ValueError("SOCKS5 username/password must be <=255 bytes")
        await conn.write(
            bytes([0x01, len(username)]) + username + bytes([len(password)]) + password
        )
        auth_reply = await conn.read_exact(2, timeout)
        if auth_reply[0] != 0x01 or auth_reply[1] != 0x00:
            raise RuntimeError("SOCKS5 username/password authentication failed")
    elif chosen[1] != 0x00:
        raise RuntimeError(f"SOCKS5 proxy selected unsupported method 0x{chosen[1]:02x}")

    host_bytes = host.encode()
    if len(host_bytes) > 255:
        raise ValueError("SOCKS5 domain host must be <=255 bytes")
    await conn.write(
        b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + struct.pack("!H", port)
    )
    header = await conn.read_exact(4, timeout)
    if header[0] != 0x05:
        raise RuntimeError("invalid SOCKS5 response version")
    if header[2] != 0x00:
        raise RuntimeError("invalid SOCKS5 reserved byte")
    if header[1] != 0x00:
        raise RuntimeError(f"SOCKS5 CONNECT failed: {socks5_reply_error(header[1])}")
    atyp = header[3]
    if atyp == 0x01:
        await conn.read_exact(4 + 2, timeout)
    elif atyp == 0x03:
        length = (await conn.read_exact(1, timeout))[0]
        await conn.read_exact(length + 2, timeout)
    elif atyp == 0x04:
        await conn.read_exact(16 + 2, timeout)
    else:
        raise RuntimeError(f"invalid SOCKS5 bound address type 0x{atyp:02x}")
