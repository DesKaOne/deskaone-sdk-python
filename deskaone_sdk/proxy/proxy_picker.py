from __future__ import annotations

import secrets
from typing import Protocol, Sequence

from .proxy_config import ProxyConfig


class NoProxyAvailableError(Exception):
    """Raised when a picker has no proxy to return."""


class ProxyPicker(Protocol):
    def pick(self) -> ProxyConfig: ...


class SingleProxyPicker:
    def __init__(self, proxy: ProxyConfig):
        self._proxies = (proxy,)

    def pick(self) -> ProxyConfig:
        return self._proxies[0]


class RoundRobinProxyPicker:
    def __init__(self, proxies: Sequence[ProxyConfig]):
        self._proxies = tuple(proxies)
        self._index = 0

    def pick(self) -> ProxyConfig:
        if not self._proxies:
            raise NoProxyAvailableError("no proxies available")
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index = (self._index + 1) % len(self._proxies)
        return proxy


class RandomProxyPicker:
    def __init__(self, proxies: Sequence[ProxyConfig]):
        self._proxies = tuple(proxies)

    def pick(self) -> ProxyConfig:
        if not self._proxies:
            raise NoProxyAvailableError("no proxies available")
        return self._proxies[secrets.randbelow(len(self._proxies))]
