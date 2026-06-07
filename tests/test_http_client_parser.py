import asyncio

from deskaone_sdk.network.http_client import (
    parse_response_headers,
    read_chunked_body,
    resolve_redirect,
)


class FakeConn:
    def __init__(self, data: bytes):
        self.data = bytearray(data)

    async def read_until(self, delimiter: bytes, max_size: int, timeout=None):
        idx = bytes(self.data).find(delimiter)
        assert idx >= 0
        end = idx + len(delimiter)
        head = bytes(self.data[:end])
        del self.data[:end]
        return head, b""

    async def read_exact(self, length: int, timeout=None):
        out = bytes(self.data[:length])
        del self.data[:length]
        return out


def test_parse_headers_and_redirect():
    version, status, reason, headers = parse_response_headers(
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nX-A: 1\r\nX-A: 2\r\n\r\n"
    )
    assert (version, status, reason) == ("HTTP/1.1", 200, "OK")
    assert headers["x-a"] == ["1", "2"]
    assert resolve_redirect("https://example.com/a/b", "../c") == "https://example.com/c"


def test_chunked_decoding():
    body = asyncio.run(
        read_chunked_body(FakeConn(b"4\r\nWiki\r\n5\r\npedia\r\n0\r\n\r\n"), 100, None)
    )
    assert body == b"Wikipedia"
