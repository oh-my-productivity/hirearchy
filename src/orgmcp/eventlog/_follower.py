"""Tailing the event files of the disk (moved from ``observe.Follower``)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from ..kernel import Clock, JsonObject, aware
from ._lines import new_events
from .api import EventFollower, EventFollowers, EventReader


class FsEventFollower(EventFollower):
    """Tails the event files: ``poll()`` returns the complete new lines of all files (today's and yesterday's day
    directories) since the last call, in time order. Files that appear later (a new process) are read from the start."""

    def __init__(
        self,
        reader: EventReader,
        clock: Clock,
        match: Callable[[JsonObject], bool] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._reader, self._clock = reader, clock
        self.match = match or (lambda ev: True)
        self.offsets: dict[Path, int] = {}
        self._seen_first = False
        self.poll(emit=False, now=now)
        self._seen_first = True

    def _files(self, now: datetime | None) -> list[Path]:
        moment = aware(now) or self._clock.now()
        return [f.path for f in self._reader.files(moment - timedelta(days=1), moment + timedelta(days=1))]

    def poll(self, emit: bool = True, now: datetime | None = None) -> list[JsonObject]:
        out: list[tuple[datetime, JsonObject]] = []
        for p in self._files(now):
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if p not in self.offsets:
                self.offsets[p] = size if not self._seen_first else 0
                if not self._seen_first:
                    continue
            if size <= self.offsets[p]:
                continue
            try:
                with open(p, "rb") as f:
                    f.seek(self.offsets[p])
                    data = f.read(size - self.offsets[p])
            except OSError:
                continue
            consumed, events = new_events(data)
            if not consumed:
                continue  # no complete line yet
            self.offsets[p] += consumed
            out.extend((t, ev) for t, ev in events if self.match(ev))
        out.sort(key=lambda item: item[0])
        return [ev for _, ev in out] if emit else []


class FsEventFollowers(EventFollowers):
    def __init__(self, reader: EventReader, clock: Clock) -> None:
        self._reader, self._clock = reader, clock

    def follow(self, match: Callable[[JsonObject], bool] | None = None, now: datetime | None = None) -> EventFollower:
        return FsEventFollower(self._reader, self._clock, match, now)
