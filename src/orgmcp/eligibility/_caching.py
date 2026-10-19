"""``CachingPauseStore``: the dashboard's decorator, which reads a flag file again only when its modification time changed."""

from __future__ import annotations

from ._ports import DirectoryProbe
from .api import PauseStore


class CachingPauseStore(PauseStore):
    def __init__(self, inner: PauseStore, probe: DirectoryProbe) -> None:
        raise NotImplementedError("red: B-eligibility")

    def paused(self, addr: str) -> str | None:
        raise NotImplementedError("red: B-eligibility")

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        raise NotImplementedError("red: B-eligibility")

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        raise NotImplementedError("red: B-eligibility")
