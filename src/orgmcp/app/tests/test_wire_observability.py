"""``wire_observability``: a builder provides the three queries of the first half of ``observability`` from the ports of the runtime, and the objects the
legacy functions use follow the runtime in force (one a test replaced a part of, or the dashboard's lenient ``Org``).

The runtime has a field for each of the seven ports of ARCHITECTURE.md 3.31 since step C-obs-2."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from orgmcp.app import wire_observability, wiring
from orgmcp.app._builder import Builder
from orgmcp.app.runtime import OrgRuntime
from orgmcp.eventlog import EventReader
from orgmcp.eventlog.testing import MemoryEventLog
from orgmcp.kernel import Clock
from orgmcp.kernel.testing import FakeClock
from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.observability import (
    EventQueries,
    IntegrityChecks,
    MetricQueries,
    NowQueries,
    ObservabilityRenderer,
    ObservabilityText,
    TraceQueries,
)
from orgmcp.observability._checks import FileIntegrityChecks
from orgmcp.observability._dispatch import ViewDispatcher
from orgmcp.observability._events import LogEventQueries
from orgmcp.observability._metrics import DerivedMetricQueries
from orgmcp.observability._now import FileNowQueries
from orgmcp.observability._render import TextObservabilityRenderer
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


def test_the_runtime_has_a_field_for_each_port_of_the_package() -> None:
    names = {f.name for f in dataclasses.fields(OrgRuntime)}
    assert {"event_queries", "trace_queries", "metric_queries", "now_queries", "integrity_checks", "observability_renderer", "observability_text"} <= names


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


def test_the_builder_has_the_second_half(tmp_path: Path) -> None:
    b = builder(tmp_path)
    assert isinstance(b.get(NowQueries), FileNowQueries) and isinstance(b.get(IntegrityChecks), FileIntegrityChecks)
    assert isinstance(b.get(ObservabilityRenderer), TextObservabilityRenderer) and isinstance(b.get(ObservabilityText), ViewDispatcher)
    assert b.get(NowQueries) is b.get(NowQueries) and list(tmp_path.iterdir()) == []


def test_the_runtime_builds_them_over_its_own_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.now_queries, NowQueries) and isinstance(runtime.integrity_checks, IntegrityChecks)
    assert isinstance(runtime.observability_renderer, ObservabilityRenderer) and isinstance(runtime.observability_text, ObservabilityText)


def test_the_objects_of_the_legacy_functions_follow_the_scheduler_of_the_runtime_in_force(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("---\nmission: test\n---\nrules\n")
    runtime = wiring.open_runtime(tmp_path)
    swapped = dataclasses.replace(runtime, scheduler_status=FakeSchedulerStatus(SchedulerState("running", 7, "x")))
    at = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    assert cast("dict[str, object]", wire_observability.now_queries_of(swapped).now_view(at)["scheduler"])["state"] == "running"
    assert cast("dict[str, object]", wire_observability.now_queries_of(runtime).now_view(at)["scheduler"])["state"] == "stopped"
    assert isinstance(wire_observability.integrity_checks_of(swapped), IntegrityChecks)
    assert isinstance(wire_observability.renderer_of(swapped), ObservabilityRenderer) and isinstance(wire_observability.observe_text_of(swapped), ObservabilityText)
