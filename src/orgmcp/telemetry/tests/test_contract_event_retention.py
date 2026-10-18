"""Contract of ``EventRetention``: day directories older than ``keep_days`` go, at least one day is always kept, nothing else is touched."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from orgmcp.telemetry import EventRetention
from orgmcp.telemetry.testing import IMPLEMENTATIONS, RetentionHarness


TODAY = datetime(2026, 10, 18, tzinfo=timezone.utc)


def day(offset: int) -> str:
    return (TODAY - timedelta(days=offset)).strftime("%Y-%m-%d")


@pytest.fixture(params=IMPLEMENTATIONS[EventRetention], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RetentionHarness:
    made = cast(Callable[[Path], RetentionHarness], request.param)(tmp_path)
    assert isinstance(made.retention, EventRetention)
    return made


def fill(h: RetentionHarness, *offsets: int) -> None:
    for offset in offsets:
        h.put_day(day(offset))


def test_only_the_days_older_than_keep_days_are_removed_oldest_first(h: RetentionHarness) -> None:
    fill(h, 0, 1, 29, 30, 31, 90)
    h.put_other("notes")
    assert h.retention.prune(30, today=TODAY) == [day(90), day(31)]
    assert h.days() == sorted([day(0), day(1), day(29), day(30)])
    assert h.others() == ["notes"]


def test_pruning_again_removes_nothing(h: RetentionHarness) -> None:
    fill(h, 0, 31)
    assert h.retention.prune(30, today=TODAY) == [day(31)]
    assert h.retention.prune(30, today=TODAY) == []


def test_at_least_one_day_is_kept_whatever_keep_days_says(h: RetentionHarness) -> None:
    fill(h, 0, 1)
    for keep in (0, -5):
        fill(h, 2)
        assert h.retention.prune(keep, today=TODAY) == [day(2)]
    assert h.days() == sorted([day(0), day(1)])


def test_today_defaults_to_now(h: RetentionHarness) -> None:
    h.put_day(day(400))
    h.put_day(h.today.strftime("%Y-%m-%d"))
    assert h.retention.prune(30) == [day(400)]
    assert h.days() == [h.today.strftime("%Y-%m-%d")]


def test_an_organization_without_events_has_nothing_to_prune(h: RetentionHarness) -> None:
    assert h.retention.prune(30, today=TODAY) == []
