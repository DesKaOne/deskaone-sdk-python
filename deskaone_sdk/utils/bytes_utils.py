from __future__ import annotations

import base64
import secrets


def bytes_to_hex(data: bytes, lower_case: bool = True) -> str:
    value = data.hex()
    return value if lower_case else value.upper()


def hex_to_bytes(value: str, allow_0x: bool = True, allow_spaces: bool = False) -> bytes:
    text = value.strip()
    if allow_0x and text.lower().startswith("0x"):
        text = text[2:]
    if allow_spaces:
        text = "".join(text.split())
    return bytes.fromhex(text)


def try_hex_to_bytes(value: str, allow_0x: bool = True) -> bytes | None:
    try:
        return hex_to_bytes(value, allow_0x=allow_0x)
    except ValueError:
        return None


def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def base64_to_bytes(value: str) -> bytes:
    return base64.b64decode(value)


def utf8_to_bytes(value: str) -> bytes:
    return value.encode()


def bytes_to_utf8(data: bytes) -> str:
    return data.decode()


def concat_bytes(*items: bytes) -> bytes:
    return b"".join(items)


def random_bytes(length: int) -> bytes:
    return secrets.token_bytes(length)
