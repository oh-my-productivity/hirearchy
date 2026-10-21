"""The event queries: the merged raw stream of the per-process event files, filtered, and followed."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import cast

from ..eventlog import EventFollowers, EventReader
from ..kernel import Clock, JsonObject, aware
from ._pure import parse_when
from ._util import iso, matcher
from .api import EventQueries


class LogEventQueries(EventQueries):
    """Reads the event files of an organization; the time is the clock's."""

    def __init__(self, reader: EventReader, followers: EventFollowers, clock: Clock) -> None:
        self._reader, self._followers, self._clock = reader, followers, clock

    def events_view(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> JsonObject:
        now = aware(now) or self._clock.now()
        lo, hi = parse_when(since, now), parse_when(until, now)
        match = matcher(agent, kind, trace, errors)
        keep: list[JsonObject] = []
        total = 0
        for _, ev in self._reader.timed(lo, hi):
            if match(ev):
                total += 1
                keep.append(ev)
                if limit and len(keep) > limit * 2:  # bounded memory on big windows
                    del keep[: len(keep) - limit]
        if limit and len(keep) > limit:
            keep = keep[-limit:]
        return {"events": keep, "total": total, "shown": len(keep), "since": iso(lo), "until": iso(hi)}

    def events(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> list[JsonObject]:
        view = self.events_view(since, until, agent, kind, trace, errors, limit, now)
        return cast("list[JsonObject]", view["events"])

    def follow(
        self, agent: str | None = None, kind: str | None = None, trace: str | None = None, errors: bool = False, poll: float = 0.5,
        max_polls: int | None = None,
    ) -> Iterator[JsonObject]:
        follower = self._followers.follow(matcher(agent, kind, trace, errors), self._clock.now())
        n = 0
        while max_polls is None or n < max_polls:
            yield from follower.poll(True, self._clock.now())
            n += 1
            if max_polls is None or n < max_polls:
                self._clock.sleep(poll)
