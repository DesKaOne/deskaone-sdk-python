from deskaone_sdk.network.handlers.socks4 import socks4_reply_error


def test_socks4_reply_error():
    assert "rejected" in socks4_reply_error(0x5B)
    assert "identd" in socks4_reply_error(0x5C)
    assert "unknown" in socks4_reply_error(0x01)
