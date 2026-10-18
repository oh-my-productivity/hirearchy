"""Reading run logs: how many there are, when they ran, how they ended."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..kernel import JsonObject, OrgLayout, stamp_of, visible
from ._format import FACTS_BYTES, HEAD_BYTES, TAIL_BYTES, cut_tail, is_failed, is_runtime_only, parse_facts
from .api import RunLogFile, RunLogReader, RunOutcomes, RunWindow


class FsRunLogReader(RunLogReader):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def _runs_dir(self, addr: str) -> Path:
        return self._paths.agent_dir(addr) / "runs"

    def _logs(self, addr: str) -> list[Path]:
        """The visible ``*.log`` files of the agent, oldest first."""
        d = self._runs_dir(addr)
        return visible(d.glob("*.log")) if d.is_dir() else []

    def count(self, addr: str) -> int:
        return len(self._logs(addr))

    def files(self, addr: str) -> list[RunLogFile]:
        return [RunLogFile(p.stem, p, stamp_of(p.stem)) for p in self._logs(addr)]

    def windows(self, addr: str) -> list[RunWindow]:
        out = []
        for p in self._logs(addr):
            start = stamp_of(p.stem)
            if start:
                out.append(RunWindow(start, max(start, datetime.fromtimestamp(p.stat().st_mtime, timezone.utc))))
        return out

    def outcomes(self, addr: str) -> RunOutcomes:
        failed: set[datetime] = set()
        runtime_only: set[datetime] = set()
        for p in self._logs(addr):
            start = stamp_of(p.stem)
            if start is None:
                continue
            try:
                with open(p, "rb") as f:
                    head = f.read(HEAD_BYTES).decode("utf-8", "replace")
                    size = f.seek(0, 2)
                    f.seek(max(0, size - TAIL_BYTES))
                    tail = f.read().decode("utf-8", "replace")
            except OSError:
                continue
            if is_failed(tail):
                failed.add(start)
            if is_runtime_only(head):
                runtime_only.add(start)
        return RunOutcomes(frozenset(failed), frozenset(runtime_only))

    def last_end(self, addr: str) -> float:
        logs = self._runs_dir(addr).glob("*.log")
        return max((p.stat().st_mtime for p in logs), default=0.0)

    def facts(self, path: Path) -> JsonObject:
        try:
            with open(path, "rb") as f:
                size = f.seek(0, 2)
                f.seek(max(0, size - FACTS_BYTES))
                tail = f.read().decode("utf-8", "replace")
        except OSError:
            return {}
        return parse_facts(tail)

    def tail(self, path: Path, max_bytes: int, max_lines: int) -> tuple[str, bool]:
        with open(path, "rb") as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - max_bytes))
            data = f.read()
        return cut_tail(data, size, max_lines)

    def head(self, path: Path, max_bytes: int) -> str:
        with open(path, "rb") as f:
            return f.read(max_bytes).decode("utf-8", errors="replace")
