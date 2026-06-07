from __future__ import annotations

import base64

from deskaone_sdk.network.tcp_connection import TcpConnection
from deskaone_sdk.proxy.proxy_config import ProxyConfig

MAX_HEADER_SIZE = 32 * 1024


class ProxyConnectError(RuntimeError):
    pass


def _authority(host: str, port: int) -> str:
    if ":" in host and not host.startswith("["):
        return f"[{host}]:{port}"
    return f"{host}:{port}"


async def http_handler_conn(
    conn: TcpConnection,
    proxy_config: ProxyConfig,
    dst_host: str,
    dst_port: int,
    timeout: float | None = None,
) -> None:
    authority = _authority(dst_host, dst_port)
    lines = [
        f"CONNECT {authority} HTTP/1.1",
        f"Host: {authority}",
        "User-Agent: DesKaOnePython/0.1.0",
        "Proxy-Connection: Keep-Alive",
    ]
    if proxy_config.username is not None:
        password = proxy_config.password or ""
        token = base64.b64encode(f"{proxy_config.username}:{password}".encode()).decode()
        lines.append(f"Proxy-Authorization: Basic {token}")
    lines.extend(["", ""])
    await conn.write("\r\n".join(lines))
    headers, _ = await conn.read_until(b"\r\n\r\n", MAX_HEADER_SIZE, timeout)
    code = parse_status_code(headers)
    if code != 200:
        auth = find_header(headers, "Proxy-Authenticate")
        detail = sanitize_header_for_error(headers)
        if auth:
            detail += f"\nProxy-Authenticate: {auth}"
        raise ProxyConnectError(f"HTTP proxy CONNECT failed with status {code}: {detail}")


def parse_status_code(headers: bytes) -> int:
    line = headers.split(b"\r\n", 1)[0].decode("iso-8859-1", "replace")
    parts = line.split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise ValueError("invalid HTTP status line")
    return int(parts[1])


def find_header(headers: bytes, name: str) -> str | None:
    needle = name.lower()
    for raw in headers.split(b"\r\n")[1:]:
        if not raw or b":" not in raw:
            continue
        key, value = raw.split(b":", 1)
        if key.decode("iso-8859-1", "replace").strip().lower() == needle:
            return value.decode("iso-8859-1", "replace").strip()
    return None


def sanitize_header_for_error(headers: bytes) -> str:
    redacted = []
    for line in headers.decode("iso-8859-1", "replace").split("\r\n"):
        if ":" in line:
            key, _ = line.split(":", 1)
            if key.strip().lower() in {"authorization", "proxy-authorization"}:
                line = f"{key}: <redacted>"
        redacted.append(line)
    return "\n".join(redacted).strip()
