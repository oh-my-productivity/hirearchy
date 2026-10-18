"""RED skeleton (step A-eventlog): tailing the event files of the disk."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..kernel import Clock, JsonObject
from .api import EventFollower, EventFollowers, EventReader


class FsEventFollower(EventFollower):
    def __init__(
        self,
        reader: EventReader,
        clock: Clock,
        match: Callable[[JsonObject], bool] | None = None,
        now: datetime | None = None,
    ) -> None:
        raise NotImplementedError("red: the real follower is not written yet")

    def poll(self, emit: bool = True, now: datetime | None = None) -> list[JsonObject]:
        raise NotImplementedError


class FsEventFollowers(EventFollowers):
    def __init__(self, reader: EventReader, clock: Clock) -> None:
        raise NotImplementedError("red: the real followers are not written yet")

    def follow(self, match: Callable[[JsonObject], bool] | None = None, now: datetime | None = None) -> EventFollower:
        raise NotImplementedError
