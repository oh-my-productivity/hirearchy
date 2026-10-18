"""RED skeleton (step A-runs): creating run logs, appending to them."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Clock, OrgLayout
from .api import RunLogSink, RunLogWriter


class FileRunLogSink(RunLogSink):
    def __init__(self, path: Path) -> None:
        raise NotImplementedError("red: A-runs")

    @property
    def path(self) -> Path:
        raise NotImplementedError("red: A-runs")

    def write(self, text: str) -> None:
        raise NotImplementedError("red: A-runs")

    def flush(self) -> None:
        raise NotImplementedError("red: A-runs")

    def close(self) -> None:
        raise NotImplementedError("red: A-runs")

    def fileno(self) -> int:
        raise NotImplementedError("red: A-runs")


class FsRunLogWriter(RunLogWriter):
    def __init__(self, paths: OrgLayout, clock: Clock) -> None:
        raise NotImplementedError("red: A-runs")

    def create(self, addr: str) -> Path:
        raise NotImplementedError("red: A-runs")

    def open_sink(self, path: Path) -> RunLogSink:
        raise NotImplementedError("red: A-runs")

    def append_note(self, rel_path: str, text: str) -> None:
        raise NotImplementedError("red: A-runs")
