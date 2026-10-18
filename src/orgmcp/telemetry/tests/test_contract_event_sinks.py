"""Contract of ``EventSinks``: one sink per organization root, and the count of what a process could not write."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import EventSink
from orgmcp.telemetry import EventSinks
from orgmcp.telemetry.testing import IMPLEMENTATIONS, SinksHarness



@pytest.fixture(params=IMPLEMENTATIONS[EventSinks], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> SinksHarness:
    made = cast(Callable[[Path], SinksHarness], request.param)(tmp_path)
    assert isinstance(made.sinks, EventSinks)
    return made


def test_the_sink_of_a_root_is_an_event_sink_and_the_same_every_time(h: SinksHarness) -> None:
    sink = h.sinks.for_root(h.root)
    assert isinstance(sink, EventSink) and h.sinks.for_root(h.root) is sink


def test_the_sinks_of_two_roots_write_to_two_logs(h: SinksHarness) -> None:
    h.sinks.for_root(h.root).emit("tick", n=1)
    h.sinks.for_root(h.other).emit("tock", n=2)
    h.sinks.for_root(h.root).emit("tick", n=3)
    assert [e["n"] for e in h.written(h.root)] == [1, 3] and [e["n"] for e in h.written(h.other)] == [2]
    assert h.sinks.for_root(h.root) is not h.sinks.for_root(h.other)


def test_nothing_is_dropped_until_something_cannot_be_written(h: SinksHarness) -> None:
    assert h.sinks.dropped() == 0
    h.sinks.for_root(h.root).emit("tick")
    assert h.sinks.dropped() == 0


def test_an_event_that_cannot_be_written_is_counted_and_never_raised(h: SinksHarness) -> None:
    h.break_storage()
    h.sinks.for_root(h.root).emit("tick")
    h.sinks.for_root(h.other).emit("tick")
    assert h.sinks.dropped() >= 2
