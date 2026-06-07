from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import ParseResult, quote, unquote, urlparse

from .proxy_type import ProxyType, proxy_type_from_string


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    type: ProxyType
    host: str
    port: int
    username: str | None = None
    password: str | None = None

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("proxy host must not be empty")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("proxy port must be between 1 and 65535")
        if not isinstance(self.type, ProxyType):
            object.__setattr__(self, "type", proxy_type_from_string(str(self.type)))

    @classmethod
    def from_url(cls, parsed_url: ParseResult) -> ProxyConfig:
        if not parsed_url.scheme:
            raise ValueError("proxy URL scheme is required")
        proxy_type = proxy_type_from_string(parsed_url.scheme)
        if parsed_url.port is None:
            raise ValueError("proxy URL port is required")
        if parsed_url.hostname is None:
            raise ValueError("proxy URL host is required")
        username = unquote(parsed_url.username) if parsed_url.username is not None else None
        password = unquote(parsed_url.password) if parsed_url.password is not None else None
        return cls(proxy_type, parsed_url.hostname, parsed_url.port, username, password)

    @classmethod
    def from_url_string(cls, value: str, default_type: ProxyType = ProxyType.HTTP) -> ProxyConfig:
        raw = value.strip()
        if not raw:
            raise ValueError("proxy URL must not be empty")
        parsed = urlparse(raw)
        if not parsed.scheme:
            raw = f"{default_type.value}://{raw}"
            parsed = urlparse(raw)
        else:
            try:
                proxy_type_from_string(parsed.scheme)
            except ValueError:
                raw = f"{default_type.value}://{raw}"
                parsed = urlparse(raw)
        return cls.from_url(parsed)

    def to_url(self) -> str:
        auth = ""
        if self.username is not None:
            auth = quote(self.username, safe="")
            if self.password is not None:
                auth += f":{quote(self.password, safe='')}"
            auth += "@"
        host = self.host
        if ":" in host and not (host.startswith("[") and host.endswith("]")):
            host = f"[{host}]"
        return f"{self.type.value}://{auth}{host}:{self.port}"

    def __str__(self) -> str:
        return self.to_url()

    def clone_with(self, **kwargs: Any) -> ProxyConfig:
        return replace(self, **kwargs)
