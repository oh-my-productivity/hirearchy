"""``FeedBuffer``: the event log in memory, extended incrementally."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import cast

from ..eventlog import EventFollowers, EventReader
from ..kernel import Clock, JsonObject, aware, parse_time
from ..observability import EventQueries, is_error
from ._const import ERROR_WINDOW, ERROR_WINDOW_TEXT, FEED_BACKFILL, FEED_KEEP
from ._events import describe
from ._ports import EventFilters
from .api import EventFeed, EventFeedFactory


class FeedBuffer(EventFeed):
    """The last ``keep`` events (oldest first), extended by polls of the event files; the errors of the last 15 minutes are kept apart.

    It starts following first, so that no event can fall between the backlog and the polls; the backlog (the last ``backfill`` of the log) is
    then loaded, and what the first polls return of it is skipped (``_seen``). A log that cannot be read means an empty feed."""

    def __init__(self, followers: EventFollowers, reader: EventReader, queries: EventQueries, filters: EventFilters, clock: Clock,
                 keep: int = FEED_KEEP, backfill: str = FEED_BACKFILL, now: datetime | None = None) -> None:
        self._filters = filters
        self._clock = clock
        self.keep = keep
        self.events: deque[JsonObject] = deque(maxlen=keep)
        self.errors: deque[tuple[datetime, JsonObject]] = deque()
        self.version = 0
        self.any = False
        self.last_ts: datetime | None = None
        now = aware(now) or clock.now()
        self._follower = followers.follow(None, now)  # first: no event can fall between the backlog and the polls
        try:
            view = queries.events_view(since=backfill, limit=keep, now=now)
            backlog = cast("list[JsonObject]", view["events"])
            errs = cast("list[JsonObject]", queries.events_view(since=ERROR_WINDOW_TEXT, errors=True, now=now)["events"])
        except Exception:  # noqa: BLE001 - a damaged log must not keep the dashboard from starting
            backlog, errs = [], []
        self._seen = {self._key(e) for e in backlog[-400:]}
        for ev in backlog:
            self._add(ev)
        for ev in errs:
            t = parse_time(ev.get("ts"))
            if t is not None:
                self.errors.append((t, ev))
        self.any = bool(backlog) or bool(reader.files())

    @staticmethod
    def _key(ev: JsonObject) -> tuple[object, object, object, object]:
        return (ev.get("proc"), ev.get("pid"), ev.get("seq"), ev.get("ts"))

    def _add(self, ev: JsonObject) -> None:
        self.events.append(ev)
        t = parse_time(ev.get("ts"))
        if t is not None and (self.last_ts is None or t > self.last_ts):
            self.last_ts = t

    def poll(self, now: datetime | None = None) -> int:
        """Read what was appended since the last poll; returns how many events were added."""
        now = aware(now) or self._clock.now()
        try:
            new = self._follower.poll(now=now)
        except Exception:  # noqa: BLE001
            new = []
        added = 0
        for ev in new:
            if self._seen:
                if self._key(ev) in self._seen:
                    continue
            self._add(ev)
            added += 1
            if is_error(ev):
                t = parse_time(ev.get("ts")) or now
                self.errors.append((t, ev))
        self._seen = set()
        if added:
            self.version += 1
            self.any = True
        cutoff = now - ERROR_WINDOW
        while self.errors and self.errors[0][0] < cutoff:
            self.errors.popleft()
        return added

    def error_count(self, now: datetime) -> int:
        cutoff = now - ERROR_WINDOW
        return sum(1 for t, _ in self.errors if t >= cutoff)

    def matching(self, text: str = "", errors: bool = False, agent: str | None = None, limit: int = 1000) -> list[JsonObject]:
        """The newest ``limit`` events that match, oldest first. ``text``: words, all of which must appear (case
        insensitive) in the agent / kind / trace / run fields; ``agent``: only events of that agent."""
        words = [w.lower() for w in text.split()]
        match = self._filters.build(agent, errors) if (agent or errors) else None
        out: list[JsonObject] = []
        for ev in reversed(self.events):
            if match is not None and not match(ev):
                continue
            if words:
                hay = " ".join(str(x) for x in (ev.get("kind"), ev.get("actor"), ev.get("agent"), ev.get("from"), ev.get("to"),
                                                ev.get("trace"), ev.get("run"), ev.get("tool"), *cast("list[object]", ev.get("traces") or ()),
                                                describe(ev))  # what the readable line says: 'refused', a title, ...
                               if x not in (None, "")).lower()
                if not all(w in hay for w in words):
                    continue
            out.append(ev)
            if len(out) >= limit:
                break
        out.reverse()
        return out


class FeedBufferFactory(EventFeedFactory):
    def __init__(self, followers: EventFollowers, reader: EventReader, queries: EventQueries, filters: EventFilters, clock: Clock) -> None:
        self._followers = followers
        self._reader = reader
        self._queries = queries
        self._filters = filters
        self._clock = clock

    def create(self, keep: int = FEED_KEEP, backfill: str = FEED_BACKFILL, now: datetime | None = None) -> EventFeed:
        return FeedBuffer(self._followers, self._reader, self._queries, self._filters, self._clock, keep, backfill, now)
