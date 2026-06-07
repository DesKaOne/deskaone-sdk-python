from deskaone_sdk.network.handlers.socks5 import socks5_reply_error


def test_socks5_reply_error():
    assert socks5_reply_error(0x05) == "connection refused"
    assert "address type" in socks5_reply_error(0x08)
    assert "unknown" in socks5_reply_error(0x99)
