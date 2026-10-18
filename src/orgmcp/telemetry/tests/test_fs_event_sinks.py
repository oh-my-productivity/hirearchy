"""``FsEventSinks``: one sink per root, made by the factory it was given, and the count of the pool."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import EventSink
from orgmcp.kernel.testing import FakeClock, ListEventSink
from orgmcp.telemetry import EventSinks
from orgmcp.telemetry._pool import EventWriterPool
from orgmcp.telemetry._sink import FsEventSinks

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-telemetry")


def make() -> tuple[FsEventSinks, EventWriterPool, list[Path]]:
    pool, made = EventWriterPool(FakeClock()), []

    def factory(root: Path) -> EventSink:
        made.append(root)
        return ListEventSink()

    return FsEventSinks(pool, factory), pool, made


def test_it_is_event_sinks() -> None:
    assert isinstance(make()[0], EventSinks)


def test_the_factory_runs_once_per_root() -> None:
    sinks, _, made = make()
    first = sinks.for_root(Path("/a"))
    assert sinks.for_root(Path("/a")) is first and sinks.for_root(Path("/b")) is not first
    assert made == [Path("/a"), Path("/b")]


def test_reset_forgets_the_sinks() -> None:
    sinks, _, made = make()
    first = sinks.for_root(Path("/a"))
    sinks.reset()
    assert sinks.for_root(Path("/a")) is not first and made == [Path("/a"), Path("/a")]


def test_dropped_is_the_count_of_the_pool() -> None:
    sinks, pool, _ = make()
    assert sinks.dropped() == 0
    pool.drop("x")
    assert sinks.dropped() == 1
