"""The event log ports in the runtime, and the legacy ``observe`` functions that now go through them. The observable behaviour is what
it was before the step: ``tests/test_observe.py`` and the golden events are the characterization."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from orgmcp import observe
from orgmcp.app import Org, wire_eventlog, wiring
from orgmcp.eventlog import ENVELOPE, EVENTS_REL, EventFile, EventFollower, EventFollowers, EventReader, event_file
from orgmcp.eventlog._follower import FsEventFollower, FsEventFollowers
from orgmcp.eventlog._reader import FsEventReader
from orgmcp.eventlog.testing import DiskEventStore, EventLogAuthor, MemoryEventLog, StoreEventLogAuthor
from orgmcp.kernel import Clock, JsonObject
from orgmcp.kernel.testing import T0, FakeClock



def stamp(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class EventLog:
    """Writes event lines into the organization the way the runtime does (what ``tests/obs_fixtures.py`` does for the legacy tests)."""

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


def test_a_reader_for_files_already_named_needs_no_organization() -> None:
    assert isinstance(wire_eventlog.system_reader(), FsEventReader)


# ------------------------------------------------------------------------------------------------ observe.py still answers


def test_observe_keeps_its_names_for_the_constants() -> None:
    assert observe.EVENTS_DIR == EVENTS_REL and observe.ENVELOPE == set(ENVELOPE) and isinstance(observe.ENVELOPE, set)


def test_event_files_are_paths_in_the_order_of_the_reader(org: Org) -> None:
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "a", proc="scheduler", pid=2)
    log.tool(stamp(2), "ceo", "b", proc="mcp", pid=1)
    log.tool(stamp(-86400 * 3), "ceo", "c", proc="cli", pid=3)
    files = observe.event_files(org)
    assert all(isinstance(p, Path) for p in files)
    assert [p.parent.name for p in files] == ["2026-10-15", "2026-10-18", "2026-10-18"]
    assert files == [f.path for f in org.runtime.event_reader.files()]
    assert [p.name.split("-")[0] for p in observe.event_files(org, stamp(-3600), stamp(3600))] == ["mcp", "scheduler"]


def test_timed_events_and_iter_events_are_the_streams_of_the_reader(org: Org) -> None:
    log = EventLog(org)
    a, b = log.tool(stamp(1), "ceo", "a"), log.tool(stamp(2), "ceo", "b")
    assert [ev for _, ev in observe.timed_events(org)] == [a, b] == list(observe.iter_events(org))
    assert [t for t, _ in observe.timed_events(org, stamp(2))] == [stamp(2)]
    stream = observe.iter_events(org)
    c = log.tool(stamp(3), "ceo", "c")
    assert list(stream) == [a, b, c]  # looked at when first iterated, as the generator functions always did


def test_the_legacy_follower_is_an_event_follower_with_the_old_signature(org: Org) -> None:
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "before")
    follower = observe.Follower(org, lambda ev: ev["tool"] != "skip", now=stamp(60))
    assert isinstance(follower, EventFollower) and EventFollower in type(follower).__mro__  # declared, not only duck-typed
    a, _, c = log.tool(stamp(2), "ceo", "a"), log.tool(stamp(3), "ceo", "skip"), log.tool(stamp(4), "ceo", "c")
    assert follower.poll(now=stamp(60)) == [a, c]
    log.tool(stamp(5), "ceo", "d")
    assert follower.poll(emit=False, now=stamp(60)) == [] and follower.poll(now=stamp(60)) == []


def test_tail_and_head_of_a_file_given_by_path(org: Org) -> None:
    log = EventLog(org)
    a, b = log.tool(stamp(1), "ceo", "a"), log.tool(stamp(2), "ceo", "b")
    (path,) = observe.event_files(org)
    assert observe._tail_events(path) == [a, b] and observe._head_event(path) == a
    assert observe._tail_events(path, 8192) == [a, b] and observe._tail_events(path.with_name("nothing.jsonl")) == []
    assert observe._head_event(path.with_name("nothing.jsonl")) is None and event_file(path).day == "2026-10-18"


def test_scheduler_files_are_start_pid_and_path_newest_first(org: Org) -> None:
    log = EventLog(org)
    log.emit("scheduler.start", stamp(1), proc="scheduler", pid=10)
    log.emit("scheduler.start", stamp(2), proc="scheduler", pid=11)
    log.emit("scheduler.start", stamp(3), proc="mcp", pid=12)
    got = observe._scheduler_files(org)
    assert [(pid, p.name.split("-")[0]) for _, pid, p in got] == [(11, "scheduler"), (10, "scheduler")]
    assert all(isinstance(ms, int) and isinstance(p, Path) for ms, _, p in got) and got[0][0] > got[1][0]
