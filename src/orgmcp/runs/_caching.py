"""RED skeleton (step A-runs): the run counter of the dashboard, cached per directory mtime."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import Clock, JsonObject, OrgLayout
from .api import RunLogFile, RunLogReader, RunOutcomes, RunWindow


@runtime_checkable
class DirectoryStamps(Protocol):
    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>``; -1 when it does not exist."""
        ...


class FsDirectoryStamps(DirectoryStamps):
    def __init__(self, paths: OrgLayout) -> None:
        raise NotImplementedError("red: A-runs")

    def mtime(self, addr: str, name: str) -> int:
        raise NotImplementedError("red: A-runs")


class CachingRunLogReader(RunLogReader):
    def __init__(self, inner: RunLogReader, stamps: DirectoryStamps, clock: Clock) -> None:
        raise NotImplementedError("red: A-runs")

    def count(self, addr: str) -> int:
        raise NotImplementedError("red: A-runs")

    def files(self, addr: str) -> list[RunLogFile]:
        raise NotImplementedError("red: A-runs")

    def windows(self, addr: str) -> list[RunWindow]:
        raise NotImplementedError("red: A-runs")

    def outcomes(self, addr: str) -> RunOutcomes:
        raise NotImplementedError("red: A-runs")

    def last_end(self, addr: str) -> float:
        raise NotImplementedError("red: A-runs")

    def facts(self, path: Path) -> JsonObject:
        raise NotImplementedError("red: A-runs")

    def tail(self, path: Path, max_bytes: int, max_lines: int) -> tuple[str, bool]:
        raise NotImplementedError("red: A-runs")

    def head(self, path: Path, max_bytes: int) -> str:
        raise NotImplementedError("red: A-runs")
