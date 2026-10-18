"""RED skeleton (step A-eventlog): the event files read from the disk."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from ..kernel import JsonObject, OrgLayout
from .api import EventFile, EventReader


class FsEventReader(EventReader):
    def __init__(self, layout: OrgLayout) -> None:
        raise NotImplementedError("red: the real reader is not written yet")

    def files(self, since: datetime | None = None, until: datetime | None = None) -> list[EventFile]:
        raise NotImplementedError

    def read_file(self, file: EventFile) -> Iterator[tuple[datetime, JsonObject]]:
        raise NotImplementedError

    def timed(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, JsonObject]]:
        raise NotImplementedError

    def events(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[JsonObject]:
        raise NotImplementedError

    def tail(self, file: EventFile, nbytes: int = 65536) -> list[JsonObject]:
        raise NotImplementedError

    def head(self, file: EventFile) -> JsonObject | None:
        raise NotImplementedError
