"""The event files read from the disk (moved from ``observe``: ``_day_dirs event_files _read_events timed_events iter_events
_tail_events _head_event``)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from ..kernel import JsonObject, OrgLayout
from ._lines import days_of, event_of, is_event_name, merged, tail_of, timed_of
from .api import EventFile, EventReader, event_file


class FsEventReader(EventReader):
    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def _day_dirs(self, since: datetime | None, until: datetime | None) -> list[Path]:
        base = self._layout.events_dir()
        try:
            names = os.listdir(base)
        except OSError:
            return []
        return [base / n for n in days_of(names, since, until) if (base / n).is_dir()]

    def files(self, since: datetime | None = None, until: datetime | None = None) -> list[EventFile]:
        out = []
        for d in self._day_dirs(since, until):
            try:
                names = sorted(n for n in os.listdir(d) if is_event_name(n))
            except OSError:
                continue
            for n in names:
                p = d / n
                try:
                    if since is not None and p.stat().st_mtime < since.timestamp():
                        continue
                except OSError:
                    continue
                out.append(event_file(p))
        return out

    def read_file(self, file: EventFile) -> Iterator[tuple[datetime, JsonObject]]:
        try:
            f = open(file.path, "rb")
        except OSError:
            return
        with f:
            yield from timed_of(f)

    def timed(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, JsonObject]]:
        yield from merged([self.read_file(f) for f in self.files(since, until)], since, until)

    def events(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[JsonObject]:
        for _, ev in self.timed(since, until):
            yield ev

    def tail(self, file: EventFile, nbytes: int = 65536) -> list[JsonObject]:
        try:
            with open(file.path, "rb") as f:
                size = f.seek(0, 2)
                f.seek(max(0, size - nbytes))
                data = f.read()
        except OSError:
            return []
        return tail_of(data, size, nbytes)

    def head(self, file: EventFile) -> JsonObject | None:
        try:
            with open(file.path, "rb") as f:
                line = f.readline()
        except OSError:
            return None
        return event_of(line)
