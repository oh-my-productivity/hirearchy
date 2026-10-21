"""The run counter of the dashboard, cached per directory mtime (what ``LenientOrg.runs_used`` did)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import Clock, JsonObject, OrgLayout, norm
from .api import RunLogFile, RunLogReader, RunOutcomes, RunWindow

TRUST_SECONDS = 2.0  # a directory modified less than this long before it was listed is listed again next time (coarse mtimes)


@runtime_checkable
class DirectoryStamps(Protocol):
    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>`` (``name`` ``""``: the agent's directory); -1 when it does not exist."""
        ...


class FsDirectoryStamps(DirectoryStamps):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def mtime(self, addr: str, name: str) -> int:
        path = self._paths.agent_dir(addr)
        try:
            return os.stat(path / name if name else path).st_mtime_ns
        except OSError:
            return -1


class CachingRunLogReader(RunLogReader):
    """The number of runs of an agent is listed again only when its ``runs`` directory changed; everything else is the inner reader's."""

    def __init__(self, inner: RunLogReader, stamps: DirectoryStamps, clock: Clock) -> None:
        self._inner = inner
        self._stamps = stamps
        self._clock = clock
        self._counts: dict[str, tuple[int, bool, int]] = {}  # agent -> (mtime of runs/, the listing is trustworthy, number of logs)

    def _trusted(self, listed_at: int, mtime: int) -> bool:
        """A listing is reused only if the directory had been quiet for a while when it was made (coarse-mtime safe)."""
        return (listed_at - mtime) > TRUST_SECONDS * 1e9

    def count(self, addr: str) -> int:
        mtime = self._stamps.mtime(addr, "runs")
        if mtime < 0:
            return 0
        key = norm(addr)
        hit = self._counts.get(key)
        if hit is not None and hit[0] == mtime and hit[1]:
            return hit[2]
        listed_at = int(self._clock.time() * 1e9)
        n = self._inner.count(addr)
        self._counts[key] = (mtime, self._trusted(listed_at, mtime), n)
        return n

    def files(self, addr: str) -> list[RunLogFile]:
        return self._inner.files(addr)

    def windows(self, addr: str) -> list[RunWindow]:
        return self._inner.windows(addr)

    def outcomes(self, addr: str) -> RunOutcomes:
        return self._inner.outcomes(addr)

    def last_end(self, addr: str) -> float:
        return self._inner.last_end(addr)

    def facts(self, path: Path) -> JsonObject:
        return self._inner.facts(path)

    def tail(self, path: Path, max_bytes: int, max_lines: int) -> tuple[str, bool]:
        return self._inner.tail(path, max_bytes, max_lines)

    def head(self, path: Path, max_bytes: int) -> str:
        return self._inner.head(path, max_bytes)
