from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TextIO
import sys

from . import term_color


@dataclass(slots=True)
class LoggerOptions:
    stream: TextIO = sys.stdout
    color: bool = True


class Logger:
    def __init__(self, name: str | None = None, options: LoggerOptions | None = None):
        self.name = name
        self.options = options or LoggerOptions()

    def info(self, message: str) -> None:
        print(self.format("INFO", message), file=self.options.stream)

    def warn(self, message: str) -> None:
        print(self.format("WARN", message), file=self.options.stream)

    def error(self, message: str) -> None:
        print(self.format("ERROR", message), file=self.options.stream)

    def success(self, message: str) -> None:
        print(self.format("SUCCESS", message), file=self.options.stream)

    def format(self, level: str, message: str, now: datetime | None = None) -> str:
        now = now or datetime.now()
        label = level.upper()
        colored = self._color(label)
        name = f" | [{self.name}]" if self.name else ""
        return f"{now:%H:%M:%S} | {colored}{name} {message}"

    def _color(self, level: str) -> str:
        if not self.options.color:
            return level
        return {
            "INFO": term_color.cyan,
            "WARN": term_color.yellow,
            "ERROR": term_color.red,
            "SUCCESS": term_color.green,
        }.get(level, lambda value: value)(level)
