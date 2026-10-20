"""Contract of ``EventFollowers``: followers start where the log is now, and each keeps its own position."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.eventlog import EventFollower, EventFollowers
from orgmcp.eventlog.testing import IMPLEMENTATIONS, EventLogHarness

from ._support import at


@pytest.fixture(params=IMPLEMENTATIONS[EventFollowers], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> EventLogHarness:
    made = cast(EventLogHarness, request.param(tmp_path))
    assert isinstance(made.followers, EventFollowers)
    return made


NOW = at(60)


def test_a_follower_is_an_event_follower_and_starts_with_nothing_new(h: EventLogHarness) -> None:
    h.log.emit(at(1), "before")
    follower = h.followers.follow(now=NOW)
    assert isinstance(follower, EventFollower)
    assert follower.poll(now=NOW) == []


def test_only_events_that_match_are_returned_and_the_others_are_not_kept_for_later(h: EventLogHarness) -> None:
    follower = h.followers.follow(lambda ev: ev["kind"] == "wanted", now=NOW)
    h.log.emit(at(1), "other")
    a = h.log.emit(at(2), "wanted")
    h.log.emit(at(3), "other")
    assert follower.poll(now=NOW) == [a]
    assert follower.poll(now=NOW) == []


def test_two_followers_do_not_share_a_position(h: EventLogHarness) -> None:
    first = h.followers.follow(now=NOW)
    a = h.log.emit(at(1), "a")
    second = h.followers.follow(now=NOW)
    b = h.log.emit(at(2), "b")
    assert first.poll(now=NOW) == [a, b]
    assert second.poll(now=NOW) == [b]


def test_without_a_time_the_followers_ask_the_clock(h: EventLogHarness) -> None:
    follower = h.followers.follow()  # the clock stands at 2026-10-18 10:00
    a = h.log.emit(at(1), "today", proc="mcp", pid=1)
    h.log.emit(at(-86400 * 5), "old", proc="mcp", pid=2)
    assert follower.poll() == [a]
    h.clock.advance(86400 * 10)  # ten days on: the old files are out of the window
    h.log.emit(at(2), "ignored", proc="mcp", pid=1)
    assert follower.poll() == []
