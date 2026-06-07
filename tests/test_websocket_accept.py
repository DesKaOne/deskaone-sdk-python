from deskaone_sdk.network.websocket_client import websocket_accept


def test_websocket_accept_rfc_example():
    assert websocket_accept("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
