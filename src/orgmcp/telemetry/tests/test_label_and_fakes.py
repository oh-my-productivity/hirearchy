"""The label and the in-memory fakes of the package."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.kernel import EventSink
from orgmcp.kernel.testing import FakeClock
from orgmcp.telemetry import ProcessLabel
from orgmcp.telemetry._label import MutableProcessLabel
from orgmcp.telemetry.testing import MemoryEventRetention, MemoryEventSinks, MemoryProcessLabel, StackTraceScope

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-telemetry")


def test_the_labels_are_labels() -> None:
    assert isinstance(MutableProcessLabel(), ProcessLabel) and isinstance(MemoryProcessLabel(), ProcessLabel)


def test_two_labels_are_independent() -> None:
    a, b = MutableProcessLabel(), MutableProcessLabel()
    a.set("mcp")
    assert b.get() == "cli"


def test_the_memory_sinks_record_per_root_and_lose_nothing_until_broken(tmp_path: Path) -> None:
    sinks = MemoryEventSinks()
    sink = sinks.for_root(tmp_path)
    assert isinstance(sink, EventSink)
    sink.emit("a", actor="ceo", x=1)
    assert [(e.kind, e.actor, e.fields) for e in sinks.events(tmp_path)] == [("a", "ceo", {"x": 1})] and sinks.events(tmp_path / "other") == []
    sinks.broken = True
    sink.emit("b")
    assert sinks.dropped() == 1 and len(sinks.events(tmp_path)) == 1


def test_the_memory_retention_removes_the_expired_days_only() -> None:
    retention = MemoryEventRetention(FakeClock(), days=["2026-01-01", "2026-10-17", "2026-10-18"], others=["notes"])
    assert retention.prune(30, today=datetime(2026, 10, 18, tzinfo=timezone.utc)) == ["2026-01-01"]
    assert retention.days == {"2026-10-17", "2026-10-18"} and retention.others == {"notes"}


def test_the_stack_scope_nests_without_threads() -> None:
    scope = StackTraceScope()
    with scope.collect() as outer:
        scope.note("a")
        with scope.collect() as inner:
            scope.note("b")
        scope.note("c")
    scope.note("lost")
    assert (outer, inner) == (["a", "c"], ["b"])
