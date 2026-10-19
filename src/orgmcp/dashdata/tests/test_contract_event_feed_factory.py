"""Contract of ``EventFeedFactory``: a feed that follows first, then loads the backlog. Over event files and over memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashdata import EventFeed, EventFeedFactory
from orgmcp.dashdata.testing import IMPLEMENTATIONS, FeedWorld

from ._support import make_feed, stamp


@pytest.fixture(params=IMPLEMENTATIONS[EventFeedFactory], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> FeedWorld:
    made = make_feed(request, tmp_path)
    assert isinstance(made.feeds, EventFeedFactory)
    return made


def test_the_factory_makes_a_feed(w: FeedWorld) -> None:
    assert isinstance(w.feeds.create(now=stamp(200)), EventFeed)


def test_every_feed_follows_on_its_own(w: FeedWorld) -> None:
    first, second = w.feeds.create(now=stamp(200)), w.feeds.create(now=stamp(200))
    w.emit(210, "tool.call", actor="ceo", tool="inbox", ok=True, ms=1)
    assert first.poll(stamp(220)) == 1 and len(second.events) == 0
    assert second.poll(stamp(220)) == 1 and len(first.events) == len(second.events) == 1


def test_an_event_written_after_the_feed_was_made_is_never_lost(w: FeedWorld) -> None:
    feed = w.feeds.create(now=stamp(200))
    for n in range(3):
        w.emit(210 + n, "tool.call", actor="ceo", tool=f"t{n}", ok=True, ms=1)
        feed.poll(stamp(220))
    assert [e["tool"] for e in feed.events] == ["t0", "t1", "t2"]


def test_a_feed_made_without_a_time_uses_the_clock(w: FeedWorld) -> None:
    w.emit(10, "tool.call", actor="ceo", tool="inbox", ok=True, ms=1)
    assert [e["tool"] for e in w.feeds.create().events] == ["inbox"]
