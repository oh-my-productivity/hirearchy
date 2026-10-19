"""``CachingPauseStore``: the dashboard's decorator, which reads a flag file again only when its modification time changed."""

from __future__ import annotations

from ..kernel import norm
from ._ports import DirectoryProbe
from .api import PauseStore


class CachingPauseStore(PauseStore):
    def __init__(self, inner: PauseStore, probe: DirectoryProbe) -> None:
        self._inner = inner
        self._probe = probe
        self._cache: dict[str, tuple[int, str | None]] = {}

    def paused(self, addr: str) -> str | None:
        a = norm(addr)
        m = self._probe.mtime(a, ".paused")
        if m < 0:
            return None
        hit = self._cache.get(a)
        if hit is not None and hit[0] == m:
            return hit[1]
        value = self._inner.paused(a)
        self._cache[a] = (m, value)
        return value

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        self._inner.pause(addr, reason, by)

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        self._inner.resume(addr, reason, by)
