"""``wire_observability``: a builder provides the three queries of the first half of ``observability`` from the ports of the runtime, and the objects the
legacy functions use follow the runtime in force (one a test replaced a part of, or the dashboard's lenient ``Org``).

The runtime has no field for them yet: all of ARCHITECTURE.md 3.31 is step C-obs-2 for ``test_runtime_fields``."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path

from orgmcp.app import wire_observability, wiring
from orgmcp.app._builder import Builder
from orgmcp.app.runtime import OrgRuntime
from orgmcp.eventlog import EventReader
from orgmcp.eventlog.testing import MemoryEventLog
from orgmcp.kernel import Clock
from orgmcp.kernel.testing import FakeClock
from orgmcp.observability import EventQueries, MetricQueries, TraceQueries
from orgmcp.observability._events import LogEventQueries
from orgmcp.observability._metrics import DerivedMetricQueries
from orgmcp.observability._trace import DerivedTraceQueries


def builder(tmp_path: Path, overrides: dict[type, object] | None = None) -> Builder:
    return Builder(tmp_path, overrides, wiring.providers())


def test_the_builder_has_the_three_queries(tmp_path: Path) -> None:
    b = builder(tmp_path)
    assert isinstance(b.get(EventQueries), LogEventQueries) and isinstance(b.get(EventQueries), EventQueries)
    assert isinstance(b.get(TraceQueries), DerivedTraceQueries) and isinstance(b.get(TraceQueries), TraceQueries)
    assert isinstance(b.get(MetricQueries), DerivedMetricQueries) and isinstance(b.get(MetricQueries), MetricQueries)
    assert b.get(EventQueries) is b.get(EventQueries)  # one per builder


def test_building_them_does_no_io(tmp_path: Path) -> None:
    b = builder(tmp_path)
    assert all(b.get(port) is not None for port in (EventQueries, TraceQueries, MetricQueries))
    assert list(tmp_path.iterdir()) == []


def test_the_runtime_has_no_field_for_them_before_the_second_half() -> None:
    names = {f.name for f in dataclasses.fields(OrgRuntime)}
    assert not {"event_queries", "trace_queries", "metric_queries"} & names


def test_the_events_are_read_through_the_event_reader_and_the_clock_of_the_builder(tmp_path: Path) -> None:
    clock, log = FakeClock(), MemoryEventLog(FakeClock())
    queries = builder(tmp_path, {Clock: clock, EventReader: log, **{}}).get(EventQueries)
    log.append("2026-10-18", "mcp-1-1.jsonl", b'{"v":1,"ts":"2026-10-18T10:00:00+00:00","kind":"tool.call","actor":"ceo"}\n')
    assert [e["kind"] for e in queries.events(since="2026-10-18T00:00:00Z", now=datetime(2026, 10, 18, 12, tzinfo=timezone.utc))] == ["tool.call"]


def test_the_objects_of_the_legacy_functions_follow_the_runtime_in_force(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    first = wire_observability.event_queries_of(runtime)
    log = MemoryEventLog(FakeClock())
    log.append("2026-10-18", "mcp-1-1.jsonl", b'{"v":1,"ts":"2026-10-18T10:00:00+00:00","kind":"tool.call","actor":"ceo"}\n')
    swapped = dataclasses.replace(runtime, event_reader=log, event_followers=log)
    got = wire_observability.event_queries_of(swapped).events(since="2026-10-18T00:00:00Z", now=datetime(2026, 10, 18, 12, tzinfo=timezone.utc))
    assert [e["kind"] for e in got] == ["tool.call"] and first.events(since="2026-10-18T00:00:00Z", now=datetime(2026, 10, 18, 12, tzinfo=timezone.utc)) == []
    assert isinstance(wire_observability.trace_queries_of(swapped), TraceQueries) and isinstance(wire_observability.metric_queries_of(swapped), MetricQueries)
