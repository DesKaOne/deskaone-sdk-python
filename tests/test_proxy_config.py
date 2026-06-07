import pytest

from deskaone_sdk.proxy import ProxyConfig, ProxyType, proxy_type_from_string


def test_proxy_type_aliases():
    assert proxy_type_from_string("https") is ProxyType.HTTP
    assert proxy_type_from_string("s4") is ProxyType.SOCKS4
    assert proxy_type_from_string("sock5") is ProxyType.SOCKS5
    with pytest.raises(ValueError):
        proxy_type_from_string("ftp")


def test_from_url_string_auth_ipv6_and_clone():
    cfg = ProxyConfig.from_url_string("socks5://user%40x:p%20w@[::1]:1080")
    assert cfg.type is ProxyType.SOCKS5
    assert cfg.host == "::1"
    assert cfg.username == "user@x"
    assert cfg.password == "p w"
    assert cfg.to_url() == "socks5://user%40x:p%20w@[::1]:1080"
    assert cfg.clone_with(port=1081).port == 1081


def test_missing_scheme_uses_default_and_requires_port():
    assert (
        str(ProxyConfig.from_url_string("user:pass@example.com:8080"))
        == "http://user:pass@example.com:8080"
    )
    with pytest.raises(ValueError):
        ProxyConfig.from_url_string("example.com")
