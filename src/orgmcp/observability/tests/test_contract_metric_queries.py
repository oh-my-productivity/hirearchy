"""Contract of ``MetricQueries``: counts, rates and percentiles over a time window; over files on disk and in memory.

Runs are the run logs of the window (so the counts equal what the files say), completed by the events of the run; tool calls, faults and
scheduler starts come from the events; messages from the message files."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.observability import MetricQueries
from orgmcp.observability.testing import IMPLEMENTATIONS, ObservabilityWorld

from . import _support
from ._support import RED, items, request, stamp, table

pytestmark = RED

SINCE = "2026-10-18T00:00:00Z"
NOW = stamp(500)


@pytest.fixture(params=_support.implementations(IMPLEMENTATIONS[MetricQueries]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ObservabilityWorld:
    made: ObservabilityWorld = request.param(tmp_path)
    assert isinstance(made.metrics, MetricQueries)
    return made


def test_an_empty_organization_has_all_the_counts_at_zero(w: ObservabilityWorld) -> None:
    m = w.metrics.metrics(since=SINCE, now=NOW)
    assert table(m, "runs") == {"total": 0, "ok": 0, "failed": 0, "timeout": 0, "killed": 0, "running": 0, "unknown": 0,
                                "duration_ms": {"n": 0, "p50": None, "p95": None, "max": None}, "queue_ms": {"n": 0, "p50": None, "p95": None, "max": None}}
    assert table(m, "tool_calls") == {"total": 0, "refused": 0, "refusal_rate": 0.0, "by_tool": {}}
    assert (m["events"], m["agent"], m["budget_spent"], m["since"], m["until"]) == (0, None, 0, stamp(-36000).isoformat(), NOW.isoformat())


def test_runs_percentiles_and_queue_waits_come_from_the_story(w: ObservabilityWorld) -> None:
    request(w)
    m = w.metrics.metrics(since=SINCE, now=stamp(200))
    runs = table(m, "runs")
    assert (runs["total"], runs["ok"], m["budget_spent"], m["events"]) == (3, 3, 3, 14)
    assert table(runs, "duration_ms") == {"n": 3, "p50": 30000.0, "p95": 42000.0, "max": 42000.0}
    queue = table(runs, "queue_ms")
    assert queue["n"] == 3 and 3000 < queue["p50"] < 51000  # type: ignore[operator]
    assert m["messages"] == {"result": 2, "task": 2}


def test_the_outcome_of_a_run_is_in_its_end_event_else_in_the_closing_lines_of_its_log(w: ObservabilityWorld) -> None:
    w.agent("ceo")
    ok = w.run_log("ceo", 10, "# exit 0 after 5s\n")
    w.run_log("ceo", 20, "# exit 1 after 6s\n")
    w.run_log("ceo", 30, "# killed after 600s timeout\n")
    w.run_log("ceo", 40, "# failed to start: no kiro\n")
    w.run_log("ceo", 50, "# killed: by the user\n")
    w.run_events("ceo", ok, 10, 5, [], [], ok=False, error="exit 1")  # the end event wins over the log
    runs = table(w.metrics.metrics(since=SINCE, now=NOW), "runs")
    assert {k: runs[k] for k in ("total", "ok", "failed", "timeout", "killed", "unknown")} == {
        "total": 5, "ok": 0, "failed": 3, "timeout": 1, "killed": 1, "unknown": 0}


def test_the_run_in_flight_is_running(w: ObservabilityWorld) -> None:
    w.agent("ceo")
    w.send("root", "ceo", "task", 0, box="inflight")
    stem = w.run_log("ceo", 10)
    w.running("ceo", stem)
    runs = table(w.metrics.metrics(since=SINCE, now=NOW), "runs")
    assert (runs["total"], runs["running"], runs["unknown"]) == (1, 1, 0)


def test_tool_calls_are_counted_by_tool_with_refusals_and_percentiles(w: ObservabilityWorld) -> None:
    for ms in (10, 20, 30, 40):
        w.tool(1, "ceo", "read", ms=ms)
    w.tool(2, "ceo", "write", ok=False, ms=7, error="no")
    tc = table(w.metrics.metrics(since=SINCE, now=NOW), "tool_calls")
    assert (tc["total"], tc["refused"], tc["refusal_rate"]) == (5, 1, 0.2)
    by_tool = table(tc, "by_tool")
    assert by_tool["read"] == {"calls": 4, "refused": 0, "refusal_rate": 0.0, "ms": {"n": 4, "p50": 20.0, "p95": 40.0, "max": 40.0}, "exceptions": 0}
    assert table(by_tool, "write")["exceptions"] == 0 and table(by_tool, "write")["refusal_rate"] == 1.0


def test_refusals_with_the_same_reason_are_grouped(w: ObservabilityWorld) -> None:
    w.tool(1, "ceo", "delegate", ok=False, error='not enough budget: you have 5 run(s); task 20261018T100003000001-root-ab12 "Ship it" in ceo/work/x.md')
    w.tool(2, "ceo/eng", "delegate", ok=False, error='not enough budget: you have 9 run(s); task 20261018T110003000001-root-cd34 "Other" in ceo/work/y.md')
    w.tool(3, "ceo", "write", ok=False, error="ceo cannot write nothing")
    top = items(w.metrics.metrics(since=SINCE, now=NOW), "top_refusals")
    assert [(t["count"], t["tools"]) for t in top] == [(2, {"delegate": 2}), (1, {"write": 1})]
    assert top[0]["message"] == "not enough budget: you have N run(s); task <id> <text> in <path>"
    assert str(top[0]["example"]).startswith("not enough budget: you have 5")


def test_what_the_scheduler_and_the_agents_went_through(w: ObservabilityWorld) -> None:
    w.emit(1, "scheduler.start", proc="scheduler", pid=1, mode="daemon")
    w.emit(100, "scheduler.start", proc="scheduler", pid=2, mode="daemon")
    w.emit(5, "scheduler.error", proc="scheduler", pid=1, phase="stall check", error="boom")
    w.emit(50, "scheduler.exit", proc="scheduler", pid=1, reason="finished: no open tasks", runs_started=2)
    w.emit(6, "stall.nudge", proc="scheduler", pid=1, task="t", to="ceo", step=0)
    w.emit(7, "agent.pause", proc="scheduler", pid=1, agent="ceo", reason="failures")
    w.emit(7, "agent.failure", proc="scheduler", pid=1, agent="ceo", count=3)
    w.emit(8, "run.orphan", proc="scheduler", pid=1, run="ceo@x", action="killed")
    m = w.metrics.metrics(since=SINCE, now=NOW)
    assert m["scheduler"] == {"starts": 2, "errors": {"stall check": 1}, "exits": {"finished: no open tasks": 1}}
    assert (m["stalls"], m["agent_failures"], m["orphans"]) == (1, 1, 1) and m["pauses"] == {"total": 1, "by_reason": {"failures": 1}}


def test_events_after_now_are_not_counted_but_the_end_of_a_run_that_started_in_the_window_is(w: ObservabilityWorld) -> None:
    w.agent("ceo")
    stem = w.run_log("ceo", 10)
    w.run_events("ceo", stem, 10, 600, [], [])  # ends at 610, after ``now``
    w.tool(900, "ceo", "late")
    m = w.metrics.metrics(since=SINCE, now=stamp(100))
    assert table(m, "tool_calls")["total"] == 0 and table(m, "runs")["ok"] == 1 and table(table(m, "runs"), "duration_ms")["p50"] == 600000.0


def test_the_window_starts_at_since_and_defaults_to_a_day(w: ObservabilityWorld) -> None:
    w.agent("ceo")
    w.run_log("ceo", -2 * 86400, "# exit 0 after 5s\n")
    w.run_log("ceo", -3600, "# exit 0 after 5s\n")
    assert table(w.metrics.metrics(now=NOW), "runs")["total"] == 1
    assert table(w.metrics.metrics(since="3d", now=NOW), "runs")["total"] == 2
    assert w.metrics.metrics(now=NOW)["since"] == stamp(500 - 86400).isoformat()


def test_a_run_of_an_agent_that_no_longer_exists_is_known_from_its_events(w: ObservabilityWorld) -> None:
    w.run_events("gone/agent", "20261018T100100000000", 60, 12, ["20261018T100000000000-root-ab12"], [], pid=1)
    m = w.metrics.metrics(since=SINCE, by="agent", now=stamp(500))
    assert table(m, "runs")["total"] == 1 and items(table(m, "by"), "rows")[0]["key"] == "gone/agent"
    assert table(table(m, "runs"), "duration_ms")["p50"] == 12000.0


def test_one_agent_only(w: ObservabilityWorld) -> None:
    for addr in ("ceo", "ceo/eng"):
        w.agent(addr)
    w.run_log("ceo", 10, "# exit 0 after 5s\n")
    w.run_log("ceo/eng", 20, "# exit 0 after 5s\n")
    w.tool(1, "ceo", "read")
    w.tool(2, "ceo/eng", "read")
    m = w.metrics.metrics(since=SINCE, now=NOW, agent=" ceo/eng ")
    assert m["agent"] == "ceo/eng" and table(m, "runs")["total"] == 1 and table(m, "tool_calls")["total"] == 1


def test_grouped_by_agent_and_by_tool(w: ObservabilityWorld) -> None:
    for addr in ("ceo", "ceo/eng"):
        w.agent(addr)
    w.run_log("ceo", 10, "# exit 0 after 5s\n")
    w.run_log("ceo/eng", 20, "# exit 1 after 5s\n")
    w.tool(1, "ceo", "read", ms=10)
    w.tool(2, "ceo/eng", "read", ms=30, ok=False, error="no")
    rows = {r["key"]: r for r in items(table(w.metrics.metrics(since=SINCE, by="agent", now=NOW), "by"), "rows")}
    assert rows["ceo"]["runs"] == 1 and rows["ceo"]["ok"] == 1 and rows["ceo/eng"]["failed"] == 1 and rows["ceo/eng"]["refused"] == 1
    assert rows["ceo/eng"]["refusal_rate"] == 1.0 and rows["ceo"]["call_ms"] == {"n": 1, "p50": 10.0, "p95": 10.0, "max": 10.0}
    by = table(w.metrics.metrics(since=SINCE, by="tool", now=NOW), "by")
    assert by["dimension"] == "tool" and [(r["key"], r["runs"], r["calls"]) for r in items(by, "rows")] == [("read", 0, 2)]


def test_grouped_by_service_and_by_trace(w: ObservabilityWorld) -> None:
    w.agent("ceo")
    memo = w.send("root", "ceo", "task", 5, service="memo", box="read")
    plain = w.send("root", "ceo", "task", 6, box="read")
    stem = w.run_log("ceo", 10, "# exit 0 after 5s\n")
    w.run_events("ceo", stem, 10, 5, [memo.id], [memo.id, plain.id])
    w.tool(11, "ceo", "delegate", trace=memo.id, args={"service": "memo"})
    w.tool(12, "ceo", "read")
    by_service = {r["key"]: r for r in items(table(w.metrics.metrics(since=SINCE, by="service", now=NOW), "by"), "rows")}
    assert (by_service["memo"]["runs"], by_service["memo"]["calls"], by_service["-"]["calls"]) == (1, 1, 1)
    by_trace = {r["key"]: r for r in items(table(w.metrics.metrics(since=SINCE, by="trace", now=NOW), "by"), "rows")}
    assert (by_trace[memo.id]["runs"], by_trace[plain.id]["runs"], by_trace["-"]["calls"]) == (1, 1, 1)


def test_an_unknown_dimension_is_refused(w: ObservabilityWorld) -> None:
    with pytest.raises(OrgError, match="by must be one of agent, tool, service, trace"):
        w.metrics.metrics(since=SINCE, by="colour", now=NOW)


def test_now_defaults_to_the_clock(w: ObservabilityWorld) -> None:
    w.clock.at(3600)
    m = w.metrics.metrics(since="1h")
    assert str(m["until"]).startswith("2026-10-18T11:00:00")
