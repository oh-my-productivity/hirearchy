"""``MemoryEventLog``: what the fake promises beyond the contract suites (it is the reader and the followers of unit tests)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.eventlog import EVENTS_REL, EventFollower, EventFollowers, EventReader, event_file
from orgmcp.eventlog.testing import MemoryEventLog
from orgmcp.kernel.testing import FakeClock

from ._support import at, day

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-eventlog")


def test_the_fake_is_the_reader_and_the_followers() -> None:
    log = MemoryEventLog()
    assert isinstance(log, EventReader) and isinstance(log, EventFollowers) and isinstance(log.follow(), EventFollower)


def test_a_new_log_has_nothing() -> None:
    assert MemoryEventLog().files() == []


def test_appending_creates_the_file_and_the_day_and_keeps_what_was_there() -> None:
    log = MemoryEventLog()
    log.append(day(0), "mcp-1-2.jsonl", b'{"ts": "2026-10-18T10:00:01+00:00", "n": 1}\n')
    log.append(day(0), "mcp-1-2.jsonl", b'{"ts": "2026-10-18T10:00:02+00:00", "n": 2}\n')
    (file,) = log.files()
    assert file.path == EVENTS_REL / day(0) / "mcp-1-2.jsonl" and (file.proc, file.pid) == ("mcp", 1)
    assert [ev["n"] for ev in log.events()] == [1, 2]


def test_a_file_is_last_written_when_the_clock_said_so() -> None:
    clock = FakeClock()
    log = MemoryEventLog(clock)
    log.append(day(0), "mcp-1-2.jsonl", b"")
    clock.advance(3600)
    log.append(day(0), "mcp-3-4.jsonl", b"")
    assert [f.pid for f in log.files(at(0))] == [1, 3]
    assert [f.pid for f in log.files(at(1800))] == [3]


def test_touch_sets_the_time_and_needs_the_file() -> None:
    log = MemoryEventLog()
    log.append(day(0), "mcp-1-2.jsonl", b"")
    log.touch(day(0), "mcp-1-2.jsonl", at(9000))
    assert len(log.files(at(8000))) == 1 and log.files(at(9001)) == []
    with pytest.raises(FileNotFoundError):
        log.touch(day(0), "nothing.jsonl", at(1))


def test_a_file_is_found_by_its_day_and_name_whatever_its_path() -> None:
    log = MemoryEventLog()
    log.append(day(0), "mcp-1-2.jsonl", b'{"ts": "2026-10-18T10:00:01+00:00", "n": 1}\n')
    elsewhere = event_file(Path("/some/other/place") / day(0) / "mcp-1-2.jsonl")
    assert [ev["n"] for _, ev in log.read_file(elsewhere)] == [1] and log.head(elsewhere) == {"ts": "2026-10-18T10:00:01+00:00", "n": 1}
    assert list(log.read_file(event_file(Path("/x") / day(1) / "mcp-1-2.jsonl"))) == []


def test_followers_made_by_the_log_see_what_is_appended_to_it() -> None:
    log = MemoryEventLog()
    follower = log.follow(now=at(60))
    log.append(day(0), "mcp-1-2.jsonl", b'{"ts": "2026-10-18T10:00:01+00:00", "n": 1}\n')
    assert [ev["n"] for ev in follower.poll(now=at(60))] == [1]
