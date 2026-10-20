"""The event log ports in the runtime. The observable behaviour is what it was before the step: ``observability/tests`` and the golden events are the
characterization."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from orgmcp.app import Org, wiring
from orgmcp.eventlog import EVENTS_REL, EventFile, EventFollowers, EventReader
from orgmcp.eventlog._follower import FsEventFollower, FsEventFollowers
from orgmcp.eventlog._reader import FsEventReader
from orgmcp.eventlog.testing import DiskEventStore, EventLogAuthor, MemoryEventLog, StoreEventLogAuthor
from orgmcp.kernel import Clock, JsonObject
from orgmcp.kernel.testing import T0, FakeClock



def stamp(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class EventLog:
    """Writes event lines into the organization the way the runtime does (what ``tests/testkit/obs_fixtures.py`` does for the legacy tests)."""

    def __init__(self, org: Org) -> None:
        self.author: EventLogAuthor = StoreEventLogAuthor(DiskEventStore(org.root / EVENTS_REL), org.root / EVENTS_REL)

    def emit(self, kind: str, ts: datetime, *, proc: str = "mcp", pid: int = 4242, **fields: object) -> JsonObject:
        return self.author.emit(ts, kind, proc=proc, pid=pid, **fields)

    def tool(self, ts: datetime, actor: str, tool: str, *, proc: str = "mcp", pid: int = 4242) -> JsonObject:
        return self.author.emit(ts, "tool.call", proc=proc, pid=pid, actor=actor, tool=tool, ok=True, ms=5)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    return Org.init(tmp_path / "org", "Test mission", {"events": False})


# ----------------------------------------------------------------------------------------------------------------- the wiring


def test_the_runtime_has_the_real_event_log_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.event_reader, FsEventReader) and isinstance(runtime.event_followers, FsEventFollowers)
    assert isinstance(runtime.event_reader, EventReader) and isinstance(runtime.event_followers, EventFollowers)
    assert isinstance(runtime.event_followers.follow(), FsEventFollower)


def test_the_reader_reads_the_events_of_the_organization_of_the_runtime(org: Org) -> None:
    ev = EventLog(org).tool(stamp(1), "ceo", "read")
    assert list(org.runtime.event_reader.events()) == [ev]
    assert org.runtime.paths.events_dir() == org.root / EVENTS_REL


class Listing(MemoryEventLog):
    """A reader that lists no file and remembers the windows it was asked for."""

    def __init__(self) -> None:
        super().__init__()
        self.asked: list[tuple[datetime | None, datetime | None]] = []

    def files(self, since: datetime | None = None, until: datetime | None = None) -> list[EventFile]:
        self.asked.append((since, until))
        return []


def test_the_followers_list_the_files_with_the_reader_of_the_runtime(tmp_path: Path) -> None:
    listing = Listing()
    runtime = wiring.open_runtime(tmp_path, {EventReader: listing})
    runtime.event_followers.follow(now=stamp(60))
    assert listing.asked == [(stamp(60) - timedelta(days=1), stamp(60) + timedelta(days=1))]


def test_the_followers_ask_the_clock_of_the_runtime_for_the_time(tmp_path: Path) -> None:
    listing, clock = Listing(), FakeClock()
    runtime = wiring.open_runtime(tmp_path, {EventReader: listing, Clock: clock})
    runtime.event_followers.follow()
    (since, until), = listing.asked
    assert since is not None and until is not None and until - since == timedelta(days=2) and since < stamp(0) < until


def test_the_event_log_is_replaced_by_the_memory_log(tmp_path: Path) -> None:
    log = MemoryEventLog()
    runtime = wiring.open_runtime(tmp_path, {EventReader: log, EventFollowers: log})
    assert runtime.event_reader is log and runtime.event_followers is log


def test_two_runtimes_do_not_share_event_objects(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).event_reader is not wiring.open_runtime(tmp_path).event_reader
