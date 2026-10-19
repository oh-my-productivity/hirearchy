"""Contract of ``EventFeed``: the event log in memory - the last events, the errors of the last 15 minutes, extended by polls. Over event files and over memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashdata import ERROR_WINDOW, EventFeed
from orgmcp.dashdata.testing import IMPLEMENTATIONS, FeedWorld

from ._support import make_feed, stamp


@pytest.fixture(params=IMPLEMENTATIONS[EventFeed], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> FeedWorld:
    made = make_feed(request, tmp_path)
    assert isinstance(made.feed, EventFeed)
    return made


def test_a_feed_over_an_empty_log_is_empty(w: FeedWorld) -> None:
    feed = w.feed
    assert (list(feed.events), feed.any, feed.version, feed.last_ts, feed.error_count(stamp(200)), feed.matching()) == ([], False, 0, None, 0, [])


def test_a_poll_brings_in_what_was_written_since(w: FeedWorld) -> None:
    w.emit(210, "tool.call", actor="ceo", tool="inbox", ok=True, ms=5)
    w.emit(215, "tool.call", actor="ceo", tool="delegate", ok=True, ms=5)
    assert w.feed.poll(stamp(220)) == 2
    assert [e["tool"] for e in w.feed.events] == ["inbox", "delegate"] and w.feed.version == 1 and w.feed.any and w.feed.last_ts == stamp(215)
    assert w.feed.poll(stamp(221)) == 0 and w.feed.version == 1  # nothing new, nothing added twice


def test_the_backlog_is_loaded_when_the_feed_is_made_and_not_added_again_by_the_polls(w: FeedWorld) -> None:
    w.emit(100, "tool.call", actor="ceo", tool="inbox", ok=True, ms=5)
    w.emit(110, "tool.call", actor="ceo", tool="write", ok=True, ms=5)
    feed = w.feeds.create(now=stamp(200))
    assert [e["tool"] for e in feed.events] == ["inbox", "write"] and feed.any and feed.last_ts == stamp(110) and feed.version == 0
    assert feed.poll(stamp(201)) == 0 and len(feed.events) == 2


def test_only_the_last_events_are_kept(w: FeedWorld) -> None:
    for n in range(5):
        w.emit(100 + n, "tool.call", actor="ceo", tool=f"t{n}", ok=True, ms=1)
    feed = w.feeds.create(keep=3, now=stamp(200))
    assert [e["tool"] for e in feed.events] == ["t2", "t3", "t4"]
    w.emit(210, "tool.call", actor="ceo", tool="t5", ok=True, ms=1)
    feed.poll(stamp(211))
    assert [e["tool"] for e in feed.events] == ["t3", "t4", "t5"]


def test_the_backlog_reaches_back_as_far_as_asked(w: FeedWorld) -> None:
    w.emit(-7000, "tool.call", actor="ceo", tool="ancient", ok=True, ms=1)
    w.emit(150, "tool.call", actor="ceo", tool="recent", ok=True, ms=1)
    assert [e["tool"] for e in w.feeds.create(backfill="1h", now=stamp(200)).events] == ["recent"]
    assert [e["tool"] for e in w.feeds.create(backfill="3h", now=stamp(200)).events] == ["ancient", "recent"]


def test_errors_are_counted_for_15_minutes(w: FeedWorld) -> None:
    w.emit(100, "tool.call", actor="ceo", tool="delegate", ok=False, error="not enough budget", error_type="OrgError", ms=1)
    w.emit(190, "tool.call", actor="ceo", tool="inbox", ok=True, ms=1)
    feed = w.feeds.create(now=stamp(200))
    assert feed.error_count(stamp(200)) == 1
    w.emit(250, "run.end", agent="ceo", ok=False, error="exit code 1", duration_ms=1000)
    feed.poll(stamp(260))
    assert feed.error_count(stamp(260)) == 2
    assert feed.error_count(stamp(100 + ERROR_WINDOW.total_seconds() + 1)) == 1  # the first has aged out of its window
    feed.poll(stamp(100 + ERROR_WINDOW.total_seconds() + 1))
    assert feed.error_count(stamp(260)) == 1  # and a poll forgets it


def test_the_feed_filters_by_words_agent_and_errors(w: FeedWorld) -> None:
    w.emit(100, "tool.call", actor="ceo", tool="delegate", ok=False, error="denied", error_type="OrgError", trace="T-1", ms=1)
    w.emit(110, "agent.pause", actor="runtime", agent="ops/audit", reason="x")
    w.emit(120, "tool.call", actor="ceo/writer", tool="write", ok=True, ms=1)
    feed = w.feeds.create(now=stamp(200))
    assert [e["kind"] for e in feed.matching(errors=True)] == ["tool.call"] and len(feed.matching("T-1")) == 1
    assert len(feed.matching("ops/audit pause")) == 1 and len(feed.matching("ceo/writer write")) == 1 and not feed.matching("nobody")
    assert [e["actor"] for e in feed.matching(agent="ceo")] == ["ceo"] and len(feed.matching(agent="ops/audit")) == 1
    assert len(feed.matching("refused")) == 1  # what the readable line says counts
    assert len(feed.matching(limit=2)) == 2 and [e["kind"] for e in feed.matching(limit=1)] == ["tool.call"]  # the newest, oldest first
