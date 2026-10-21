"""``wire_observability``: a builder provides the queries of ``observability`` from the ports of the runtime.

The runtime has a field for each of the seven ports of ARCHITECTURE.md 3.31 since step C-obs-2."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path

from hirearchy.app import wiring
from hirearchy.app._builder import Builder
from hirearchy.app.runtime import OrgRuntime
from hirearchy.eventlog import EventReader
from hirearchy.eventlog.testing import MemoryEventLog
from hirearchy.kernel import Clock
from hirearchy.kernel.testing import FakeClock
from hirearchy.observability import (
    EventQueries,
    IntegrityChecks,
    MetricQueries,
    NowQueries,
    ObservabilityRenderer,
    ObservabilityText,
    TraceQueries,
)
from hirearchy.observability._checks import FileIntegrityChecks
from hirearchy.observability._dispatch import ViewDispatcher
from hirearchy.observability._events import LogEventQueries
from hirearchy.observability._metrics import DerivedMetricQueries
from hirearchy.observability._now import FileNowQueries
from hirearchy.observability._render import TextObservabilityRenderer
from hirearchy.observability._trace import DerivedTraceQueries


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


def test_the_runtime_has_a_field_for_each_port_of_the_package() -> None:
    names = {f.name for f in dataclasses.fields(OrgRuntime)}
    assert {"event_queries", "trace_queries", "metric_queries", "now_queries", "integrity_checks", "observability_renderer", "observability_text"} <= names


def test_the_events_are_read_through_the_event_reader_and_the_clock_of_the_builder(tmp_path: Path) -> None:
    clock, log = FakeClock(), MemoryEventLog(FakeClock())
    queries = builder(tmp_path, {Clock: clock, EventReader: log, **{}}).get(EventQueries)
    log.append("2026-10-18", "mcp-1-1.jsonl", b'{"v":1,"ts":"2026-10-18T10:00:00+00:00","kind":"tool.call","actor":"ceo"}\n')
    assert [e["kind"] for e in queries.events(since="2026-10-18T00:00:00Z", now=datetime(2026, 10, 18, 12, tzinfo=timezone.utc))] == ["tool.call"]


def test_the_builder_has_the_second_half(tmp_path: Path) -> None:
    b = builder(tmp_path)
    assert isinstance(b.get(NowQueries), FileNowQueries) and isinstance(b.get(IntegrityChecks), FileIntegrityChecks)
    assert isinstance(b.get(ObservabilityRenderer), TextObservabilityRenderer) and isinstance(b.get(ObservabilityText), ViewDispatcher)
    assert b.get(NowQueries) is b.get(NowQueries) and list(tmp_path.iterdir()) == []


def test_the_runtime_builds_them_over_its_own_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.now_queries, NowQueries) and isinstance(runtime.integrity_checks, IntegrityChecks)
    assert isinstance(runtime.observability_renderer, ObservabilityRenderer) and isinstance(runtime.observability_text, ObservabilityText)

