"""RED skeleton (step A-runs): reading run logs."""

from __future__ import annotations

from pathlib import Path

from ..kernel import JsonObject, OrgLayout
from .api import RunLogFile, RunLogReader, RunOutcomes, RunWindow


class FsRunLogReader(RunLogReader):
    def __init__(self, paths: OrgLayout) -> None:
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
