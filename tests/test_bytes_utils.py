from deskaone_sdk.utils import (
    base64_to_bytes,
    bytes_to_base64,
    bytes_to_hex,
    bytes_to_utf8,
    concat_bytes,
    hex_to_bytes,
    random_bytes,
    try_hex_to_bytes,
    utf8_to_bytes,
)


def test_bytes_utils():
    assert bytes_to_hex(b"\x0f", lower_case=False) == "0F"
    assert hex_to_bytes("0x0f") == b"\x0f"
    assert hex_to_bytes("0 f", allow_spaces=True) == b"\x0f"
    assert try_hex_to_bytes("zz") is None
    assert base64_to_bytes(bytes_to_base64(b"ok")) == b"ok"
    assert bytes_to_utf8(utf8_to_bytes("halo")) == "halo"
    assert concat_bytes(b"a", b"b") == b"ab"
    assert len(random_bytes(4)) == 4
