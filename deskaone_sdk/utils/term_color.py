from __future__ import annotations

import os

_enabled = "NO_COLOR" not in os.environ


def set_term_color_enabled(value: bool) -> None:
    global _enabled
    _enabled = value


def _wrap(code: str, value: str) -> str:
    if not _enabled:
        return value
    return f"\033[{code}m{value}\033[0m"


def red(value: str) -> str:
    return _wrap("31", value)


def green(value: str) -> str:
    return _wrap("32", value)


def yellow(value: str) -> str:
    return _wrap("33", value)


def blue(value: str) -> str:
    return _wrap("34", value)


def magenta(value: str) -> str:
    return _wrap("35", value)


def cyan(value: str) -> str:
    return _wrap("36", value)


def white(value: str) -> str:
    return _wrap("37", value)


def gray(value: str) -> str:
    return _wrap("90", value)


def bold(value: str) -> str:
    return _wrap("1", value)


def dim(value: str) -> str:
    return _wrap("2", value)


def italic(value: str) -> str:
    return _wrap("3", value)


def underline(value: str) -> str:
    return _wrap("4", value)


def inverse(value: str) -> str:
    return _wrap("7", value)


def strike(value: str) -> str:
    return _wrap("9", value)


def rgb(value: str, r: int, g: int, b: int) -> str:
    return _wrap(f"38;2;{r};{g};{b}", value)


def xterm(value: str, code: int) -> str:
    return _wrap(f"38;5;{code}", value)
