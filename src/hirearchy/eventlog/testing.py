"""In-memory event log, the authoring helpers of the tests, and the registry the contract suites iterate over.

``MemoryEventLog`` is the reader and the followers at once, over files that are byte strings in a dictionary (so a partial last
line can be written to it, as a live writer leaves one). The contract suites run against it and against the disk readers.
``EventLogHarness`` writes event lines "the way the runtime does" (one file per process per UTC day, ``seq`` counting the lines of
one file) into whichever of the two the suite is checking: the tests never import the writer.
"""

from __future__ import annotations

import io
import json
import os
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from hirearchy.kernel import Clock, JsonObject, OrgPaths, aware
from hirearchy.kernel.testing import T0, FakeClock

from ._follower import FsEventFollowers
from ._lines import days_of, event_of, is_event_name, merged, new_events, tail_of, timed_of
from ._reader import FsEventReader
from .api import EVENTS_REL, EventFile, EventFollower, EventFollowers, EventReader, event_file


class EventStore(Protocol):
    """Where the bytes of an event log are: the two primitives that the authoring helper needs."""

    def append(self, day: str, name: str, data: bytes) -> None:
        """Append to ``<day>/<name>`` (the file and the directory are created)."""
        ...

    def touch(self, day: str, name: str, when: datetime) -> None:
        """Set the modification time of ``<day>/<name>``."""
        ...


class MemoryEventFollower(EventFollower):
    """Tails a ``MemoryEventLog``: the same positions and windows as the disk follower, over byte strings."""

    def __init__(self, log: MemoryEventLog, match: Callable[[JsonObject], bool] | None = None, now: datetime | None = None) -> None:
        self._log = log
        self._match = match or (lambda ev: True)
        self._offsets: dict[tuple[str, str], int] = {}
        self._seen_first = False
        self.poll(emit=False, now=now)
        self._seen_first = True

    def poll(self, emit: bool = True, now: datetime | None = None) -> list[JsonObject]:
        moment = aware(now) or self._log.clock.now()
        out: list[tuple[datetime, JsonObject]] = []
        for file in self._log.files(moment - timedelta(days=1), moment + timedelta(days=1)):
            key = (file.day, file.path.name)
            data = self._log.content(*key)
            if key not in self._offsets:
                self._offsets[key] = len(data) if not self._seen_first else 0
                if not self._seen_first:
                    continue
            if len(data) <= self._offsets[key]:
                continue
            consumed, events = new_events(data[self._offsets[key] :])
            self._offsets[key] += consumed
            out.extend((t, ev) for t, ev in events if self._match(ev))
        out.sort(key=lambda item: item[0])
        return [ev for _, ev in out] if emit else []


class MemoryEventLog(EventReader, EventFollowers, EventStore):
    """The event log in memory: day directory -> file name -> bytes, each file with the time it was last written."""

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or FakeClock()
        self._days: dict[str, dict[str, bytearray]] = {}
        self._written: dict[tuple[str, str], float] = {}

    # ---- the store (how tests put bytes in)
    def append(self, day: str, name: str, data: bytes) -> None:
        self._days.setdefault(day, {}).setdefault(name, bytearray()).extend(data)
        self._written[(day, name)] = self.clock.time()

    def touch(self, day: str, name: str, when: datetime) -> None:
        if name not in self._days.get(day, {}):
            raise FileNotFoundError(f"{day}/{name}")
        self._written[(day, name)] = when.timestamp()

    def content(self, day: str, name: str) -> bytes:
        """The bytes of ``<day>/<name>`` (none when there is no such file)."""
        return bytes(self._days.get(day, {}).get(name, b""))

    # ---- the reader
    def files(self, since: datetime | None = None, until: datetime | None = None) -> list[EventFile]:
        out = []
        for day in days_of(self._days, since, until):
            for name in sorted(n for n in self._days[day] if is_event_name(n)):
                if since is not None and self._written[(day, name)] < since.timestamp():
                    continue
                out.append(event_file(EVENTS_REL / day / name))
        return out

    def read_file(self, file: EventFile) -> Iterator[tuple[datetime, JsonObject]]:
        return timed_of(io.BytesIO(self.content(file.day, file.path.name)))

    def timed(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, JsonObject]]:
        yield from merged([self.read_file(f) for f in self.files(since, until)], since, until)

    def events(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[JsonObject]:
        for _, ev in self.timed(since, until):
            yield ev

    def tail(self, file: EventFile, nbytes: int = 65536) -> list[JsonObject]:
        data = self.content(file.day, file.path.name)
        return tail_of(data[max(0, len(data) - nbytes) :], len(data), nbytes)

    def head(self, file: EventFile) -> JsonObject | None:
        return event_of(self.content(file.day, file.path.name).split(b"\n", 1)[0])

    # ---- the followers
    def follow(self, match: Callable[[JsonObject], bool] | None = None, now: datetime | None = None) -> EventFollower:
        return MemoryEventFollower(self, match, now)


class DiskEventStore(EventStore):
    """``<root>/.runtime/events`` on the disk, written by hand."""

    def __init__(self, events_dir: Path) -> None:
        self.base = events_dir

    def append(self, day: str, name: str, data: bytes) -> None:
        path = self.base / day / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:
            f.write(data)

    def touch(self, day: str, name: str, when: datetime) -> None:
        stamp = when.timestamp()
        os.utime(self.base / day / name, (stamp, stamp))


class EventLogAuthor(Protocol):
    """Writes event lines into a log the way the runtime does, for the tests."""

    def file(self, day: str, proc: str, pid: int) -> EventFile:
        """The file of this process on this day (its name carries the start of the process, allocated on first use)."""
        ...

    def emit(self, ts: datetime, kind: str = "tool.call", *, proc: str = "mcp", pid: int = 4242, **fields: object) -> JsonObject:
        """Append one complete line to the file of ``proc``/``pid`` on the UTC day of ``ts``; the file is last written at the latest
        ``ts`` it holds. Returns the event."""
        ...

    def raw(self, day: str, proc: str, pid: int, text: str) -> EventFile:
        """Append text as it is (a line being written has no newline yet)."""
        ...

    def foreign(self, day: str, name: str, data: bytes = b"") -> None:
        """Put a file of any name (not an event file when the name says so) in a day directory."""
        ...

    def touch(self, file: EventFile, when: datetime) -> None:
        """Set the time the file was last written."""
        ...


class StoreEventLogAuthor(EventLogAuthor):
    def __init__(self, store: EventStore, base: Path) -> None:
        self._store = store
        self._base = base
        self._started: dict[tuple[str, int], int] = {}
        self._seq: dict[tuple[str, str], int] = {}
        self._mtime: dict[tuple[str, str], datetime] = {}

    def file(self, day: str, proc: str, pid: int) -> EventFile:
        start_ms = self._started.setdefault((proc, pid), int(T0.timestamp() * 1000) + len(self._started))
        return event_file(self._base / day / f"{proc}-{pid}-{start_ms}.jsonl")

    def emit(self, ts: datetime, kind: str = "tool.call", *, proc: str = "mcp", pid: int = 4242, **fields: object) -> JsonObject:
        target = self.file(ts.astimezone(timezone.utc).strftime("%Y-%m-%d"), proc, pid)
        key = (target.day, target.path.name)
        self._seq[key] = self._seq.get(key, 0) + 1
        event: JsonObject = {
            "v": 1, "ts": ts.isoformat(), "seq": self._seq[key], "proc": proc, "pid": pid, "kind": kind,
            "actor": "runtime", "run": None, "trace": None, **fields,
        }
        self._store.append(*key, (json.dumps(event) + "\n").encode())
        self._mtime[key] = max(self._mtime.get(key, ts), ts)
        self._store.touch(*key, self._mtime[key])
        return event

    def raw(self, day: str, proc: str, pid: int, text: str) -> EventFile:
        target = self.file(day, proc, pid)
        self._store.append(day, target.path.name, text.encode())
        return target

    def foreign(self, day: str, name: str, data: bytes = b"") -> None:
        self._store.append(day, name, data)

    def touch(self, file: EventFile, when: datetime) -> None:
        self._store.touch(file.day, file.path.name, when)


@dataclass(frozen=True)
class EventLogHarness:
    """One implementation under test: the readers, the clock they use, and the way to put events where they look."""

    reader: EventReader
    followers: EventFollowers
    clock: FakeClock
    log: EventLogAuthor


def fs_event_log(tmp_path: Path) -> EventLogHarness:
    paths = OrgPaths(tmp_path)
    clock = FakeClock()
    reader = FsEventReader(paths)
    return EventLogHarness(
        reader, FsEventFollowers(reader, clock), clock, StoreEventLogAuthor(DiskEventStore(paths.events_dir()), paths.events_dir())
    )


def memory_event_log(tmp_path: Path) -> EventLogHarness:
    clock = FakeClock()
    memory = MemoryEventLog(clock)
    return EventLogHarness(memory, memory, clock, StoreEventLogAuthor(memory, EVENTS_REL))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    EventReader: [fs_event_log, memory_event_log],
    EventFollower: [fs_event_log, memory_event_log],
    EventFollowers: [fs_event_log, memory_event_log],
}
