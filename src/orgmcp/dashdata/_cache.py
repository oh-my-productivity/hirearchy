"""``DashCache``: the state the five queries of one dashboard share."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar, cast

from .api import DashboardState, EventFeed, EventFeedFactory, Snapshot
from ._ports import DashClock, MtimeProbe

T = TypeVar("T")


class DashCache(DashboardState):
    """The time of the dashboard, the answers kept for a few seconds (``memoised``), the directory times of the refresh in progress
    (``refresh`` / ``mtime``), the event feed and the last snapshot.

    NOT THREAD-SAFE. A dashboard is read from one thread at a time: the application serialises its refreshes (the Textual app runs one
    worker at a time and waits for it before the next), and so do the callers of the queries. Two threads inside the queries at once would
    interleave ``refresh`` with the reads that rely on it and could hand out a half-built answer; nothing here locks, because nothing needs
    to while that rule holds (and a lock would only hide a second refresh that should not have started)."""

    def __init__(self, clock: DashClock, probe: MtimeProbe, feeds: EventFeedFactory) -> None:
        self._clock = clock
        self._probe = probe
        self._feeds = feeds
        self._memo: dict[str, tuple[tuple[object, ...], float, object]] = {}
        self.feed: EventFeed | None = None
        self.snap: Snapshot | None = None
        self.check_result: tuple[datetime, str, bool] | None = None

    def now(self) -> datetime:
        return self._clock.now()

    def refresh(self) -> None:
        self._probe.tick()

    def mtime(self, addr: str, name: str) -> int:
        return self._probe.mtime(addr, name)

    def memoised(self, name: str, sig: tuple[object, ...], ttl: float, fn: Callable[[], T]) -> T:
        hit = self._memo.get(name)
        if hit is not None and hit[0] == sig and self._clock.monotonic() - hit[1] < ttl:
            return cast(T, hit[2])
        value = fn()
        self._memo[name] = (sig, self._clock.monotonic(), value)
        return value

    def following(self, now: datetime) -> EventFeed:
        if self.feed is None:
            self.feed = self._feeds.create(now=now)
        else:
            self.feed.poll(now)
        return self.feed
