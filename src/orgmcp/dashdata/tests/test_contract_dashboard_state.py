"""Contract of ``DashboardState``: what the queries of one dashboard share - the time, the answers kept for a few seconds, the directory times of a refresh,
the event feed, the last snapshot. Real (``DashCache``) and fake."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashdata import DashboardState
from orgmcp.dashdata.testing import IMPLEMENTATIONS, MemoryEventFeed, StateWorld

from ._support import make_state, stamp


@pytest.fixture(params=IMPLEMENTATIONS[DashboardState], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> StateWorld:
    made = make_state(request, tmp_path)
    assert isinstance(made.state, DashboardState)
    return made


def test_a_new_state_has_nothing_yet(w: StateWorld) -> None:
    assert (w.state.feed, w.state.snap, w.state.check_result) == (None, None, None) and w.state.now() == stamp(200)


def test_a_refresh_begins(w: StateWorld) -> None:
    w.state.refresh()
    w.state.refresh()
    assert w.refreshed() == 2


def test_the_time_of_a_directory_is_what_it_has_or_minus_one(w: StateWorld) -> None:
    w.touch("ceo", "inbox", 123)
    assert w.state.mtime("ceo", "inbox") == 123 and w.state.mtime("ceo", "read") == -1


def test_an_answer_is_kept_while_its_signature_is_the_same_and_it_is_young(w: StateWorld) -> None:
    calls: list[int] = []

    def made() -> list[int]:
        calls.append(1)
        return [len(calls)]

    first = w.state.memoised("services", (1, 2), 5.0, made)
    assert w.state.memoised("services", (1, 2), 5.0, made) is first and len(calls) == 1
    w.clock.advance(4.9)
    assert w.state.memoised("services", (1, 2), 5.0, made) is first
    w.clock.advance(0.2)
    assert w.state.memoised("services", (1, 2), 5.0, made) is not first and len(calls) == 2


def test_an_answer_is_made_again_when_its_signature_changes_and_each_name_has_its_own(w: StateWorld) -> None:
    first = w.state.memoised("health", (1,), 5.0, lambda: ["a"])
    assert w.state.memoised("health", (2,), 5.0, lambda: ["b"]) == ["b"]
    assert w.state.memoised("requests", (2,), 5.0, lambda: ["c"]) == ["c"] and first == ["a"]


def test_the_feed_is_made_at_the_first_call_and_polled_at_the_following_ones(w: StateWorld) -> None:
    feed = w.state.following(stamp(200))
    assert isinstance(feed, MemoryEventFeed) and w.state.feed is feed and w.feeds.asked == [(5000, "2h", stamp(200))]
    assert w.state.following(stamp(210)) is feed and feed.polled == [stamp(210)] and len(w.feeds.asked) == 1


def test_the_snapshot_and_the_check_are_remembered(w: StateWorld) -> None:
    w.state.check_result = (stamp(200), "all passed", True)
    assert w.state.check_result == (stamp(200), "all passed", True)
