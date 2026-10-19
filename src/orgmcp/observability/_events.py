"""The event queries. (RED: skeleton.)"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from ..eventlog import EventFollowers, EventReader
from ..kernel import Clock, JsonObject
from .api import EventQueries


class LogEventQueries(EventQueries):
    def __init__(self, reader: EventReader, followers: EventFollowers, clock: Clock) -> None:
        self._reader, self._followers, self._clock = reader, followers, clock

    def events_view(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> JsonObject:
        raise NotImplementedError("red: C-obs-1")

    def events(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> list[JsonObject]:
        raise NotImplementedError("red: C-obs-1")

    def follow(
        self, agent: str | None = None, kind: str | None = None, trace: str | None = None, errors: bool = False, poll: float = 0.5,
        max_polls: int | None = None,
    ) -> Iterator[JsonObject]:
        raise NotImplementedError("red: C-obs-1")
