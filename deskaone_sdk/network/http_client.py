from __future__ import annotations

import json as json_module
from dataclasses import dataclass
from typing import Any
from urllib.parse import ParseResult, urljoin, urlparse

from deskaone_sdk.network.tcp_client import TCPClient
from deskaone_sdk.proxy.proxy_config import ProxyConfig
from deskaone_sdk.proxy.proxy_picker import ProxyPicker


class HttpClientError(Exception):
    pass


@dataclass(slots=True)
class HttpResponse:
    uri: str | ParseResult
    version: str
    status_code: int
    reason_phrase: str
    headers: dict[str, list[str]]
    body: bytes

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code <= 299

    def header(self, name: str) -> str | None:
        values = self.headers.get(name.lower())
        return values[-1] if values else None

    def text(self, encoding: str = "utf-8", errors: str = "replace") -> str:
        return self.body.decode(encoding, errors)

    def json(self) -> Any:
        return json_module.loads(self.text())


class HttpClient:
    def __init__(
        self,
        *,
        timeout: float = 30.0,
        read_timeout: float = 30.0,
        proxy_config: ProxyConfig | None = None,
        proxy_picker: ProxyPicker | None = None,
        local_addr: tuple[str, int] | None = None,
        ssl_context=None,
        verify_ssl: bool = True,
        user_agent: str = "DesKaOnePython/0.1.0",
        max_header_size: int = 32 * 1024,
        max_body_size: int = 10 * 1024 * 1024,
        max_redirects: int = 5,
    ):
        self.timeout = timeout
        self.read_timeout = read_timeout
        self.proxy_config = proxy_config
        self.proxy_picker = proxy_picker
        self.local_addr = local_addr
        self.ssl_context = ssl_context
        self.verify_ssl = verify_ssl
        self.user_agent = user_agent
        self.max_header_size = max_header_size
        self.max_body_size = max_body_size
        self.max_redirects = max_redirects

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes | str | None = None,
        follow_redirects: bool = True,
    ) -> HttpResponse:
        current = url
        redirects = 0
        while True:
            response = await self._request_once(method, current, headers, body)
            if not follow_redirects or response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.header("location")
            if not location:
                return response
            redirects += 1
            if redirects > self.max_redirects:
                raise HttpClientError("maximum redirects exceeded")
            current = resolve_redirect(current, location)
            if response.status_code == 303:
                method = "GET"
                body = None

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("GET", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("DELETE", url, **kwargs)

    async def post(self, url: str, body: bytes | str | None = None, **kwargs: Any) -> HttpResponse:
        return await self.request("POST", url, body=body, **kwargs)

    async def put(self, url: str, body: bytes | str | None = None, **kwargs: Any) -> HttpResponse:
        return await self.request("PUT", url, body=body, **kwargs)

    async def patch(self, url: str, body: bytes | str | None = None, **kwargs: Any) -> HttpResponse:
        return await self.request("PATCH", url, body=body, **kwargs)

    async def post_json(
        self, url: str, value: Any, headers: dict[str, str] | None = None, **kwargs: Any
    ) -> HttpResponse:
        merged = {**(headers or {}), "Content-Type": "application/json"}
        return await self.post(url, json_module.dumps(value), headers=merged, **kwargs)

    async def _request_once(
        self, method: str, url: str, headers: dict[str, str] | None, body: bytes | str | None
    ) -> HttpResponse:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise HttpClientError("URL must be http(s) and include a host")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        secure = parsed.scheme == "https"
        client = TCPClient(
            timeout=self.timeout,
            proxy_config=self.proxy_config,
            proxy_picker=self.proxy_picker,
            local_addr=self.local_addr,
            secure=secure,
            ssl_context=self.ssl_context,
            verify_ssl=self.verify_ssl,
        )
        conn = await client.connect(parsed.hostname, port)
        try:
            body_bytes = body.encode() if isinstance(body, str) else (body or b"")
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"
            request_headers = {
                "Host": _host_header(parsed.hostname, port, secure),
                "User-Agent": self.user_agent,
                "Accept-Encoding": "identity",
                "Connection": "close",
                **(headers or {}),
            }
            if body is not None:
                request_headers["Content-Length"] = str(len(body_bytes))
            for key, value in request_headers.items():
                _validate_header(key, value)
            raw = [f"{method.upper()} {path} HTTP/1.1"]
            raw.extend(f"{key}: {value}" for key, value in request_headers.items())
            raw.extend(["", ""])
            await conn.write("\r\n".join(raw).encode() + body_bytes)
            head, _ = await conn.read_until(b"\r\n\r\n", self.max_header_size, self.read_timeout)
            version, status, reason, parsed_headers = parse_response_headers(head)
            response_body = await read_response_body(
                conn, parsed_headers, self.max_body_size, self.read_timeout
            )
            return HttpResponse(url, version, status, reason, parsed_headers, response_body)
        finally:
            await conn.close()


def _host_header(host: str, port: int, secure: bool) -> str:
    default = 443 if secure else 80
    display = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return display if port == default else f"{display}:{port}"


def _validate_header(name: str, value: str) -> None:
    if not name or any(ch in name for ch in "\r\n:") or "\r" in value or "\n" in value:
        raise HttpClientError("invalid HTTP header")


def parse_response_headers(data: bytes) -> tuple[str, int, str, dict[str, list[str]]]:
    text = data.decode("iso-8859-1", "replace")
    lines = text.split("\r\n")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2 or not parts[0].startswith("HTTP/") or not parts[1].isdigit():
        raise HttpClientError("invalid HTTP response status line")
    headers: dict[str, list[str]] = {}
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            raise HttpClientError("invalid HTTP response header")
        key, value = line.split(":", 1)
        headers.setdefault(key.strip().lower(), []).append(value.strip())
    return parts[0], int(parts[1]), parts[2] if len(parts) > 2 else "", headers


async def read_response_body(
    conn, headers: dict[str, list[str]], max_size: int, timeout: float | None
) -> bytes:
    transfer = ",".join(headers.get("transfer-encoding", [])).lower()
    if "chunked" in transfer:
        return await read_chunked_body(conn, max_size, timeout)
    content_length = headers.get("content-length")
    if content_length:
        length = int(content_length[-1])
        if length > max_size:
            raise HttpClientError("response body too large")
        return await conn.read_exact(length, timeout)
    out = bytearray()
    while True:
        chunk = await conn.read_some(65536, timeout)
        if not chunk:
            break
        out += chunk
        if len(out) > max_size:
            raise HttpClientError("response body too large")
    return bytes(out)


async def read_chunked_body(conn, max_size: int, timeout: float | None) -> bytes:
    body = bytearray()
    while True:
        line, _ = await conn.read_until(b"\r\n", 8192, timeout)
        size_text = line[:-2].split(b";", 1)[0].decode("ascii", "strict")
        size = int(size_text, 16)
        if size == 0:
            while True:
                trailer, _ = await conn.read_until(b"\r\n", 32 * 1024, timeout)
                if trailer == b"\r\n":
                    return bytes(body)
        if len(body) + size > max_size:
            raise HttpClientError("response body too large")
        body += await conn.read_exact(size, timeout)
        crlf = await conn.read_exact(2, timeout)
        if crlf != b"\r\n":
            raise HttpClientError("invalid chunk terminator")


def resolve_redirect(base: str, location: str) -> str:
    return urljoin(base, location)
