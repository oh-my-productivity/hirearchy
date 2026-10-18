"""The decorators the dashboard puts on the agent ports: listings kept per directory change, charters per file change."""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from typing import Protocol, runtime_checkable

from ..kernel import ROOT, Clock, JsonObject, OrgLayout, norm
from ._tree import TreeDirectory
from .api import AgentDirectory, CharterReader

CACHE_TRUST = 2.0  # a directory modified less than this many seconds before it was listed is listed again next time
PLACEHOLDER_ROLE = "?"  # the role of a charter that could not be read


@runtime_checkable
class DirectoryProbe(Protocol):
    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>`` (the agent's directory itself for ``name`` ``""``); -1 when it is not there."""
        ...


@runtime_checkable
class CharterStamps(Protocol):
    def stamp(self, addr: str) -> tuple[int, int]:
        """``(mtime_ns, size)`` of ``<addr>/AGENT.md``; ``OSError`` when it cannot be looked at (missing)."""
        ...


class FsDirectoryProbe(DirectoryProbe):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def mtime(self, addr: str, name: str) -> int:
        path = self._paths.agent_dir(addr)
        try:
            return os.stat(path / name if name else path).st_mtime_ns
        except OSError:
            return -1


class FsCharterStamps(CharterStamps):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def stamp(self, addr: str) -> tuple[int, int]:
        st = (self._paths.agent_dir(addr) / "AGENT.md").stat()
        return (st.st_mtime_ns, st.st_size)


class CachingAgentDirectory(TreeDirectory):
    """The children of an agent are listed again only when its directory changed, or was changed so recently when they were listed
    that a second change within the same tick could have gone unseen (``CACHE_TRUST``)."""

    def __init__(self, inner: AgentDirectory, probe: DirectoryProbe, clock: Clock) -> None:
        self._inner = inner
        self._probe = probe
        self._clock = clock
        self._kids: dict[str, tuple[int, bool, list[str]]] = {}

    def exists(self, addr: str) -> bool:
        return self._inner.exists(addr)

    def children(self, addr: str) -> list[str]:
        a = norm(addr)
        mtime = self._probe.mtime(a, "")
        if mtime < 0:
            return []
        hit = self._kids.get(a)
        if hit is not None and hit[0] == mtime and hit[1]:
            return hit[2]
        listed_at = int(self._clock.time() * 1e9)
        kids = self._inner.children(a)
        self._kids[a] = (mtime, (listed_at - mtime) > CACHE_TRUST * 1e9, kids)
        return kids


class LenientCharterReader(CharterReader):
    """A charter is parsed once per change of its file; one that cannot be read is a placeholder, and is reported in ``problems``
    under ``<addr>/AGENT.md`` by the name of the error."""

    def __init__(self, inner: CharterReader, stamps: CharterStamps, problems: MutableMapping[str, str]) -> None:
        self._inner = inner
        self._stamps = stamps
        self._problems = problems
        self._charters: dict[str, tuple[tuple[int, int], tuple[JsonObject, str]]] = {}

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        a = norm(addr)
        if a == ROOT:
            return self._inner.charter(a)
        try:
            stamp = self._stamps.stamp(a)
            hit = self._charters.get(a)
            if hit is not None and hit[0] == stamp:
                return hit[1]
            value = self._inner.charter(a)
            self._charters[a] = (stamp, value)
            self._problems.pop(f"{a}/AGENT.md", None)
            return value
        except Exception as exc:  # noqa: BLE001 - a dashboard keeps going; the problem is listed instead
            self._problems[f"{a}/AGENT.md"] = type(exc).__name__
            return {"role": PLACEHOLDER_ROLE}, ""

    def memory(self, addr: str) -> str:
        return self._inner.memory(addr)
