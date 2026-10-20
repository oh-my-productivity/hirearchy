"""Characterization: what the views say about the scenario organizations, key for key and number for number.

The expected files were captured from ``observe.py`` before the package existed (``_scenario``); the queries are built over the ports of the
runtime of the same organizations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from orgmcp.observability._derive import LogTraceDerivers
from orgmcp.observability._events import LogEventQueries
from orgmcp.observability._history import IndexedMessageHistory
from orgmcp.observability._metrics import DerivedMetricQueries
from orgmcp.observability._runs import RunCollector
from orgmcp.observability._trace import DerivedTraceQueries
from orgmcp.observability._util import plain

from . import _scenario
from ._scenario import NOW, SINCE, stamp
from ._support import expected



def dump(data: object) -> str:
    """What ``cli obs ... --json`` prints."""
    return json.dumps(plain(data), indent=2, default=str) + "\n"


class Queries:
    """The three views over the ports of an organization's runtime."""

    def __init__(self, org: Any) -> None:
        rt = org.runtime
        history = IndexedMessageHistory(rt.message_index)
        collector = RunCollector(rt.run_log_reader, rt.run_registry, rt.agents, rt.mailbox, rt.event_reader)
        self.history = history
        self.events = LogEventQueries(rt.event_reader, rt.event_followers, rt.clock)
        self.traces = DerivedTraceQueries(history, LogTraceDerivers(rt.run_log_reader), rt.event_reader, collector, rt.agents, rt.clock)
        self.metrics = DerivedMetricQueries(rt.event_reader, collector, history, rt.clock)


@pytest.fixture
def q(built: Any) -> Queries:
    return Queries(built.org)


EVENTS: dict[str, dict[str, Any]] = {
    "all": dict(since=SINCE), "errors": dict(since=SINCE, errors=True), "agent_limit": dict(since=SINCE, agent="ceo/eng", limit=3),
    "kind_run": dict(since=SINCE, kind="run"), "kind_tool": dict(since=SINCE, kind="tool.call", limit=5),
    "window": dict(since=stamp(10), until=stamp(70)), "relative": dict(since="3m", until="now"),
}
METRICS: dict[str, dict[str, Any]] = {
    "plain": {}, "by_agent": dict(by="agent"), "by_tool": dict(by="tool"), "by_service": dict(by="service"), "by_trace": dict(by="trace"),
    "agent": dict(agent="ceo", by="tool"), "narrow": dict(since="2m"),
}


@pytest.mark.parametrize("name", EVENTS)
def test_the_event_views(q: Queries, name: str) -> None:
    assert dump(q.events.events_view(now=NOW, **EVENTS[name])) == expected(f"events_{name}.json")


def test_the_event_view_of_a_trace(q: Queries, built: Any) -> None:
    assert dump(q.events.events_view(now=NOW, since=SINCE, trace=built.task.id)) == expected("events_trace.json")


@pytest.mark.parametrize("name", METRICS)
def test_the_metrics(q: Queries, name: str) -> None:
    kw = {"since": SINCE, **METRICS[name]}
    assert dump(q.metrics.metrics(now=NOW, **kw)) == expected(f"metrics_{name}.json")


def test_the_trace_of_the_request(q: Queries, built: Any) -> None:
    assert dump(q.traces.trace(built.task.id, NOW)) == expected("trace_recorded.json")


def test_the_trace_of_a_message_of_the_request_is_the_trace_of_the_request(q: Queries, built: Any) -> None:
    assert dump(q.traces.trace(built.sub.id, NOW)) == expected("trace_of_message.json")


def test_the_trace_of_the_rework(q: Queries, built: Any) -> None:
    assert dump(q.traces.trace(built.again.id, NOW)) == expected("trace_rework.json")


def test_the_messages_of_the_history(q: Queries) -> None:
    assert dump({k: v.__dict__ for k, v in q.history.messages().items()}) == expected("messages_recorded.json")


def test_the_trace_when_no_message_records_its_request(tmp_path: Path, clock: Any) -> None:
    built = _scenario.story(tmp_path, clock, record=False)
    q = Queries(built.org)
    assert dump(q.traces.trace(built.task.id, NOW)) == expected("trace_derived.json")
    assert dump({k: v.__dict__ for k, v in q.history.messages().items()}) == expected("messages_derived.json")


def test_the_trace_when_the_organization_has_no_events(tmp_path: Path, clock: Any) -> None:
    built = _scenario.story(tmp_path, clock, events=False)
    q = Queries(built.org)
    assert dump(q.traces.trace(built.task.id, NOW)) == expected("trace_noevents.json")
    assert dump({k: v.__dict__ for k, v in q.history.messages().items()}) == expected("messages_noevents.json")
