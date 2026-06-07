import pytest

from deskaone_sdk.proxy import (
    NoProxyAvailableError,
    ProxyConfig,
    ProxyType,
    RandomProxyPicker,
    RoundRobinProxyPicker,
    SingleProxyPicker,
)


def _cfg(port: int) -> ProxyConfig:
    return ProxyConfig(ProxyType.HTTP, "127.0.0.1", port)


def test_single_and_round_robin():
    first, second = _cfg(1), _cfg(2)
    assert SingleProxyPicker(first).pick() == first
    picker = RoundRobinProxyPicker([first, second])
    assert [picker.pick(), picker.pick(), picker.pick()] == [first, second, first]


def test_empty_and_immutable():
    proxies = [_cfg(1)]
    picker = RandomProxyPicker(proxies)
    proxies.clear()
    assert picker.pick().port == 1
    with pytest.raises(NoProxyAvailableError):
        RoundRobinProxyPicker([]).pick()
