"""``FsEventFollower``: how it lists, stats and reads the files (the shared behaviour is in ``test_contract_event_followers``)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from hirearchy.eventlog import EventFile, EventFollower, EventFollowers, event_file
from hirearchy.eventlog._follower import FsEventFollower, FsEventFollowers
from hirearchy.eventlog._reader import FsEventReader
from hirearchy.eventlog.testing import EventLogHarness, MemoryEventLog, fs_event_log
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import FakeClock

from ._support import at, day

NOW = at(60)


class ListingSpy(MemoryEventLog):
    """The reader that the follower asks for its files, remembering the windows it was asked for and listing what it is told."""

    def __init__(self, listed: list[EventFile]) -> None:
        super().__init__()
        self.listed = listed
        self.windows: list[tuple[datetime | None, datetime | None]] = []

    def files(self, since: datetime | None = None, until: datetime | None = None) -> list[EventFile]:
        self.windows.append((since, until))
        return list(self.listed)


@pytest.fixture
def h(tmp_path: Path) -> EventLogHarness:
    return fs_event_log(tmp_path)


def test_followers_are_event_followers_and_make_followers(tmp_path: Path) -> None:
    followers = FsEventFollowers(FsEventReader(OrgPaths(tmp_path)), FakeClock())
    follower = followers.follow(now=NOW)
    assert isinstance(followers, EventFollowers) and isinstance(follower, FsEventFollower) and isinstance(follower, EventFollower)


def test_the_files_asked_for_are_the_day_before_to_the_day_after_now(tmp_path: Path) -> None:
    spy = ListingSpy([])
    FsEventFollowers(spy, FakeClock()).follow(now=NOW)
    assert spy.windows == [(NOW - timedelta(days=1), NOW + timedelta(days=1))]  # at construction (the first, silent poll)
    follower = FsEventFollowers(spy, FakeClock()).follow(now=NOW)
    follower.poll(now=at(3600))
    assert spy.windows[-1] == (at(3600) - timedelta(days=1), at(3600) + timedelta(days=1))


def test_a_time_without_a_zone_is_utc(tmp_path: Path) -> None:
    spy = ListingSpy([])
    follower = FsEventFollowers(spy, FakeClock()).follow(now=datetime(2026, 10, 18, 10, 0))
    follower.poll(now=datetime(2026, 10, 18, 11, 0))
    assert spy.windows[-1] == (at(3600) - timedelta(days=1), at(3600) + timedelta(days=1))
    assert all(t is not None and t.tzinfo is not None for window in spy.windows for t in window)


def test_without_a_time_the_clock_decides(tmp_path: Path) -> None:
    clock, spy = FakeClock(), ListingSpy([])
    follower = FsEventFollowers(spy, clock).follow()
    clock.advance(7200)
    follower.poll()
    first, second = spy.windows[0][0], spy.windows[1][0]
    assert first is not None and second is not None and second - first >= timedelta(hours=2)


def test_a_listed_file_that_cannot_be_statted_is_left_for_later(tmp_path: Path) -> None:
    ghost = event_file(tmp_path / day(0) / "mcp-1-2.jsonl")
    follower = FsEventFollowers(ListingSpy([ghost]), FakeClock()).follow(now=NOW)
    assert follower.poll(now=NOW) == []
    ghost.path.parent.mkdir()
    ghost.path.write_text('{"ts": "2026-10-18T10:00:02+00:00", "kind": "k"}\n')
    assert [ev["kind"] for ev in follower.poll(now=NOW)] == ["k"]  # it appeared after the follower started: read from its start


def test_a_listed_file_that_cannot_be_opened_is_skipped(tmp_path: Path) -> None:
    spy = ListingSpy([])
    follower = FsEventFollowers(spy, FakeClock()).follow(now=NOW)
    in_the_way = tmp_path / day(0) / "mcp-1-2.jsonl"
    in_the_way.mkdir(parents=True)  # a directory: it may have a size, and cannot be read as a file
    spy.listed = [event_file(in_the_way)]
    assert follower.poll(now=NOW) == []


def test_a_multibyte_line_is_read_whole_however_the_writes_were_cut(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    line = '{"ts": "2026-10-18T10:00:02+00:00", "kind": "k", "text": "héllo wörld ✓"}\n'.encode()
    cut = line.index("ö".encode()) + 1  # in the middle of a two-byte character
    h.log.foreign(day(0), h.log.file(day(0), "mcp", 1).path.name, line[:cut])
    assert follower.poll(now=NOW) == []
    h.log.foreign(day(0), h.log.file(day(0), "mcp", 1).path.name, line[cut:])
    (event,) = follower.poll(now=NOW)
    assert event["text"] == "héllo wörld ✓"


def test_the_position_is_kept_per_file(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    a1 = h.log.emit(at(1), "a1", proc="mcp", pid=1)
    b1 = h.log.emit(at(2), "b1", proc="mcp", pid=2)
    assert follower.poll(now=NOW) == [a1, b1]
    b2 = h.log.emit(at(3), "b2", proc="mcp", pid=2)
    assert follower.poll(now=NOW) == [b2]
