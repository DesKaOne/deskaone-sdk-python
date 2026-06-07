from __future__ import annotations

from enum import Enum


class ProxyType(str, Enum):
    HTTP = "http"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


def proxy_type_from_string(value: str) -> ProxyType:
    normalized = value.strip().lower()
    aliases = {
        "http": ProxyType.HTTP,
        "https": ProxyType.HTTP,
        "s4": ProxyType.SOCKS4,
        "sock4": ProxyType.SOCKS4,
        "socks4": ProxyType.SOCKS4,
        "s5": ProxyType.SOCKS5,
        "sock5": ProxyType.SOCKS5,
        "socks5": ProxyType.SOCKS5,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported proxy type: {value!r}") from exc
