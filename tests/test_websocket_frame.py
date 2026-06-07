import asyncio

from deskaone_sdk.network.websocket_client import (
    WebSocketOpcode,
    decode_close_payload,
    encode_close_payload,
    encode_frame,
    mask_payload,
    read_frame,
)


class FakeConn:
    def __init__(self, data: bytes):
        self.data = bytearray(data)

    async def read_exact(self, length: int, timeout=None):
        out = bytes(self.data[:length])
        del self.data[:length]
        return out


def test_client_frame_masking():
    frame = encode_frame(WebSocketOpcode.TEXT, b"hi", mask=True)
    assert frame[1] & 0x80
    key = frame[2:6]
    assert mask_payload(frame[6:], key) == b"hi"


def test_server_frame_and_close_payload():
    frame = encode_frame(WebSocketOpcode.BINARY, b"abc", mask=False)
    opcode, payload, fin = asyncio.run(read_frame(FakeConn(frame), 100))
    assert (opcode, payload, fin) == (WebSocketOpcode.BINARY, b"abc", True)
    assert decode_close_payload(encode_close_payload(1000, "bye")) == (1000, "bye")
