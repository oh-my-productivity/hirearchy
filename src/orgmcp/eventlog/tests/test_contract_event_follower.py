"""Contract of ``EventFollower``: what ``poll`` returns, for the disk and for the in-memory log."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.eventlog import EventFollower, EventFollowers
from orgmcp.eventlog.testing import IMPLEMENTATIONS, EventLogHarness
from orgmcp.kernel import JsonObject

from ._support import at, day, implementations


@pytest.fixture(params=implementations(EventFollower, IMPLEMENTATIONS[EventFollower]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> EventLogHarness:
    made = cast(EventLogHarness, request.param(tmp_path))
    assert isinstance(made.followers, EventFollowers)
    return made


NOW = at(60)


def kinds(events: list[JsonObject]) -> list[object]:
    return [ev["kind"] for ev in events]


def test_lines_appended_to_a_file_are_returned_once_in_order(h: EventLogHarness) -> None:
    h.log.emit(at(1), "before")
    follower = h.followers.follow(now=NOW)
    a = h.log.emit(at(2), "first")
    b = h.log.emit(at(3), "second")
    assert follower.poll(now=NOW) == [a, b]
    assert follower.poll(now=NOW) == []
    c = h.log.emit(at(4), "third")
    assert follower.poll(now=NOW) == [c]


def test_a_file_that_appears_later_is_read_from_its_start(h: EventLogHarness) -> None:
    h.log.emit(at(1), "before", proc="mcp", pid=1)
    follower = h.followers.follow(now=NOW)
    a = h.log.emit(at(2), "first", proc="scheduler", pid=2)  # a new process
    b = h.log.emit(at(3), "second", proc="scheduler", pid=2)
    assert follower.poll(now=NOW) == [a, b]


def test_an_empty_file_that_exists_when_the_follower_starts_is_read_from_its_start(h: EventLogHarness) -> None:
    h.log.raw(day(0), "mcp", 1, "")  # created, nothing in it yet
    follower = h.followers.follow(now=NOW)
    a = h.log.emit(at(2), "first", proc="mcp", pid=1)
    assert follower.poll(now=NOW) == [a]


def test_a_line_is_returned_only_when_it_is_complete(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    h.log.raw(day(0), "mcp", 1, '{"v": 1, "ts": "2026-10-18T10:00:02+00:00", "kind": "late"')
    assert follower.poll(now=NOW) == []
    h.log.raw(day(0), "mcp", 1, ', "seq": 1}\n{"v": 1, "ts": "2026-10-18T10:00:03+00:00", "kind": "next"')
    assert kinds(follower.poll(now=NOW)) == ["late"]
    h.log.raw(day(0), "mcp", 1, "}\n")
    assert kinds(follower.poll(now=NOW)) == ["next"]
    assert follower.poll(now=NOW) == []


def test_lines_that_are_not_events_are_consumed_and_skipped(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    h.log.raw(day(0), "mcp", 1, 'garbage\n[1]\n"s"\n{"kind": "no ts"}\n{"ts": "bad", "kind": "bad ts"}\n\n')
    a = h.log.emit(at(2), "real", proc="mcp", pid=1)
    assert follower.poll(now=NOW) == [a]
    assert follower.poll(now=NOW) == []


def test_one_poll_merges_the_files_by_time(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    h.log.emit(at(5), "e5", proc="mcp", pid=1)
    h.log.emit(at(2), "e2", proc="scheduler", pid=2)
    h.log.emit(at(9), "e9", proc="mcp", pid=1)
    h.log.emit(at(7), "e7", proc="cli", pid=3)
    assert kinds(follower.poll(now=NOW)) == ["e2", "e5", "e7", "e9"]


def test_polling_without_emitting_only_moves_the_position(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    h.log.emit(at(1), "skipped")
    assert follower.poll(emit=False, now=NOW) == []
    a = h.log.emit(at(2), "seen")
    assert follower.poll(now=NOW) == [a]


def test_the_files_followed_are_those_of_the_day_before_to_the_day_after_now(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    h.log.emit(at(-86400 * 3), "three days ago", proc="mcp", pid=1)
    yesterday = h.log.emit(at(-86400 + 100), "yesterday", proc="mcp", pid=2)
    tomorrow = h.log.emit(at(86400), "tomorrow", proc="mcp", pid=3)
    h.log.emit(at(86400 * 3), "in three days", proc="mcp", pid=4)
    assert follower.poll(now=NOW) == [yesterday, tomorrow]


def test_a_file_outside_the_window_is_read_when_the_window_reaches_it(h: EventLogHarness) -> None:
    follower = h.followers.follow(now=NOW)
    a = h.log.emit(at(86400 * 3), "far", proc="mcp", pid=1)
    assert follower.poll(now=NOW) == []
    assert follower.poll(now=at(86400 * 3)) == [a]
    assert follower.poll(now=at(86400 * 3)) == []


