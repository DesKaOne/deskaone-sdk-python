from __future__ import annotations

import base64
import hashlib
import time
import zipfile
from pathlib import Path

NAME = "deskaone-sdk-python"
DIST = "deskaone_sdk_python"
VERSION = "0.1.0"


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    wheel_name = f"{DIST}-{VERSION}-py3-none-any.whl"
    out = Path(wheel_directory) / wheel_name
    records: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in Path("deskaone_sdk").rglob("*.py"):
            _write(zf, records, path.as_posix(), path.read_bytes())
        dist_info = f"{DIST}-{VERSION}.dist-info"
        _write(zf, records, f"{dist_info}/METADATA", _metadata().encode())
        _write(zf, records, f"{dist_info}/WHEEL", _wheel().encode())
        _write(zf, records, f"{dist_info}/top_level.txt", b"deskaone_sdk\n")
        record_path = f"{dist_info}/RECORD"
        rows = [f"{name},sha256={_digest(data)},{len(data)}" for name, data in records]
        rows.append(f"{record_path},,")
        zf.writestr(record_path, "\n".join(rows) + "\n")
    return wheel_name


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    wheel_name = f"{DIST}-{VERSION}-py3-none-any.whl"
    out = Path(wheel_directory) / wheel_name
    root = Path.cwd().as_posix()
    records: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        dist_info = f"{DIST}-{VERSION}.dist-info"
        pth = f"{DIST}.pth"
        _write(zf, records, pth, f"{root}\n".encode())
        _write(zf, records, f"{dist_info}/METADATA", _metadata().encode())
        _write(zf, records, f"{dist_info}/WHEEL", _wheel().encode())
        _write(zf, records, f"{dist_info}/top_level.txt", b"deskaone_sdk\n")
        record_path = f"{dist_info}/RECORD"
        rows = [f"{name},sha256={_digest(data)},{len(data)}" for name, data in records]
        rows.append(f"{record_path},,")
        zf.writestr(record_path, "\n".join(rows) + "\n")
    return wheel_name


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    dist_info = Path(metadata_directory) / f"{DIST}-{VERSION}.dist-info"
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(_metadata())
    (dist_info / "WHEEL").write_text(_wheel())
    (dist_info / "top_level.txt").write_text("deskaone_sdk\n")
    return dist_info.name


def get_requires_for_build_wheel(config_settings=None):
    return []


def get_requires_for_build_editable(config_settings=None):
    return []


def _write(zf, records, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, time.localtime()[:6])
    info.external_attr = (0o644 & 0xFFFF) << 16
    zf.writestr(info, data)
    records.append((name, data))


def _digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def _metadata() -> str:
    return "\n".join(
        [
            "Metadata-Version: 2.3",
            f"Name: {NAME}",
            f"Version: {VERSION}",
            "Summary: Async Python SDK foundation for DesKaOne networking and proxy features.",
            "Author: DesKaOne",
            "License-Expression: MIT",
            "Requires-Python: >=3.11",
            "Provides-Extra: dev",
            "Requires-Dist: pytest; extra == 'dev'",
            "Requires-Dist: ruff; extra == 'dev'",
            "",
        ]
    )


def _wheel() -> str:
    return "Wheel-Version: 1.0\nGenerator: deskaone-minimal-backend\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
