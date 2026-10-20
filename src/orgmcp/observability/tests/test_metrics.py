# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import os
import sys
import time

import pytest
import testkit
from testkit import observability_world as observe
from testkit.legacy.orgmcp.core import ROOT, Org, OrgError
from testkit.health_world import Scheduler
from testkit.obs_fixtures import EventLog, Story, stamp
from testkit.observability_world import freeze

FAKE = str(testkit.FAKE_AGENT)
NOW = stamp(200)


@pytest.fixture
def org(tmp_path):
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/testkit/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(org):
    return freeze(org)


@pytest.fixture
def story(org, clock):
    return Story(org, clock)


def sched_org(org, tasks=1, mode="work"):
    """A real scheduler run on the fake agents (real run logs, real messages, no events)."""

    def runner(o, addr, prompt):
        return [sys.executable, FAKE], o.dir(addr), {**os.environ, "ORG_ROOT": str(o.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    made = [org.delegate(ROOT, "ceo", f"Job {i}", "goal", "criteria", budget=6) for i in range(tasks)]
    s = Scheduler(org, runner, echo=lambda _: None)
    s.acquire()
    try:
        for _ in range(500):
            if not s.tick():
                break
            time.sleep(0.02)
    finally:
        s.release()
    return made


# ------------------------------------------------------------------------------------------------ metrics
def test_metrics_percentiles_are_exact_and_counts_equal_the_files(org, clock):
    log = EventLog(org)
    durations = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for i, secs in enumerate(durations):
        clock.at(i * 1000)
        task = org.delegate(ROOT, "ceo", f"T{i}", "g", "a", budget=3)
        clock.at(i * 1000 + 2)
        batch = [m.id for m in org.begin_run("ceo")]
        p = org.start_run_log("ceo")
        org.end_run("ceo", True)
        log.run("ceo", p.stem, stamp(i * 1000 + 2), secs, batch, [task.id], ok=i != 3, error=None if i != 3 else "boom")
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(20_000))
    assert m["runs"]["total"] == 10 == len(list((org.dir("ceo") / "runs").glob("*.log")))
    assert m["runs"]["ok"] == 9 and m["runs"]["failed"] == 1
    assert m["runs"]["duration_ms"] == {"n": 10, "p50": 50_000, "p95": 100_000, "max": 100_000}
    assert m["runs"]["queue_ms"]["n"] == 10 and m["runs"]["queue_ms"]["p50"] == pytest.approx(2005, abs=50)
    assert m["budget_spent"] == 10 and m["messages"] == {"task": 10}


def test_metrics_run_counts_per_agent_equal_run_logs_in_the_window(org):
    sched_org(org, tasks=1)
    m = observe.metrics(org, since="24h", by="agent", now=None)
    rows = {r["key"]: r for r in m["by"]["rows"]}
    for agent in ("ceo", "ceo/eng"):
        in_files = len([p for p in (org.dir(agent) / "runs").glob("*.log")])
        assert rows[agent]["runs"] == in_files == org.runs_used(agent)
    assert m["runs"]["total"] == org.runs_used("ceo") + org.runs_used("ceo/eng")
    assert m["runs"]["ok"] == m["runs"]["total"] and m["events"] == 0
    assert "no events in this window" in observe.render_metrics(m)


def test_metrics_window_excludes_older_runs(org, clock):
    clock.at(0)
    org.delegate(ROOT, "ceo", "A", "g", "a", budget=5)
    org.begin_run("ceo")
    old = org.start_run_log("ceo")
    org.end_run("ceo", True)
    clock.at(7200)
    org.delegate(ROOT, "ceo", "B", "g", "a", budget=5)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.end_run("ceo", True)
    assert observe.metrics(org, since="1h", now=stamp(7300))["runs"]["total"] == 1
    assert observe.metrics(org, since="3h", now=stamp(7300))["runs"]["total"] == 2
    assert observe.metrics(org, since=stamp(-5), now=stamp(7300))["runs"]["total"] == 2
    assert old.exists()


def test_metrics_tools_refusals_and_top_refusal_messages(org, story):
    log = EventLog(org)
    for i in range(3):  # the same reason with different numbers and ids
        log.tool(stamp(150 + i), "ceo", "delegate", ok=False, ms=2 + i,
                 error=f'not enough budget: you have {i} run(s); task 20261018T10000{i}000001-root-ab1{i} "Job {i}"')
    log.tool(stamp(160), "ceo/eng", "write", ok=False, error="you may only write inside your own directory (got ceo/x.md)")
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=NOW)
    d = m["tool_calls"]["by_tool"]["delegate"]
    assert d["calls"] == 2 + 1 + 3 + 0 and d["refused"] == 4  # story: 2 delegates (+root's), one refused; plus 3 more
    assert m["tool_calls"]["refused"] == 5
    top = m["top_refusals"][0]
    assert top["count"] == 3 and top["tools"] == {"delegate": 3} and "<id>" in top["message"] and "N run(s)" in top["message"]
    assert m["top_refusals"][1]["count"] == 1
    text = observe.render_metrics(m)
    assert "top refusals:" in text and "3x not enough budget" in text
    assert d["ms"]["n"] == 6 and d["ms"]["max"] == 5


def test_metrics_by_dimensions(org, story):
    since = "2026-10-18T00:00:00Z"
    by_agent = {r["key"]: r for r in observe.metrics(org, since=since, by="agent", now=NOW)["by"]["rows"]}
    assert by_agent["ceo"]["runs"] == 2 and by_agent["ceo/eng"]["runs"] == 1 and by_agent["ceo"]["calls"] == 4
    by_tool = {r["key"]: r for r in observe.metrics(org, since=since, by="tool", now=NOW)["by"]["rows"]}
    assert by_tool["delegate"]["calls"] == 3 and by_tool["delegate"]["refused"] == 1 and by_tool["write"]["calls"] == 1
    by_trace = observe.metrics(org, since=since, by="trace", now=NOW)["by"]["rows"]
    assert {r["key"] for r in by_trace} == {story.task.id, "-"} and next(r for r in by_trace if r["key"] == story.task.id)["runs"] == 3
    assert observe.metrics(org, since=since, by="service", now=NOW)["by"]["rows"][0]["key"] == "-"
    with pytest.raises(OrgError, match="by must be"):
        observe.metrics(org, by="colour")
    assert "by agent:" in observe.render_metrics(observe.metrics(org, since=since, by="agent", now=NOW))


def test_metrics_outcomes_from_events_and_log_tails(org, clock):
    log = EventLog(org)
    for i, (kw, tail) in enumerate([
        ({}, "# exit 0 after 5s\n"),
        ({"ok": False}, "# exit 1 after 5s\n"),
        ({"ok": False, "timed_out": True, "killed": True}, "# killed after 9s timeout\n# exit -9 after 9s\n"),
        ({"ok": False, "killed": True}, "# interrupted by scheduler shutdown\n"),
    ]):
        clock.at(i * 100)
        org.delegate(ROOT, "ceo", f"T{i}", "g", "a", budget=2)
        batch = [m.id for m in org.begin_run("ceo")]
        p = org.start_run_log("ceo")
        org.end_run("ceo", True)
        p.write_text(tail)
        log.run("ceo", p.stem, stamp(i * 100), 5, batch, [], **kw)
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(1000))["runs"]
    assert (m["ok"], m["failed"], m["timeout"], m["killed"]) == (1, 1, 1, 1)
    # without events the run logs say the same
    for p in (org.root / ".runtime" / "events").rglob("*.jsonl"):
        p.unlink()
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(1000))["runs"]
    assert (m["ok"], m["failed"], m["timeout"], m["killed"]) == (1, 1, 1, 1)


def test_metrics_scheduler_stalls_pauses(org, clock):
    log = EventLog(org)
    log.emit("scheduler.start", stamp(1), proc="scheduler", pid=1, mode="daemon")
    log.emit("scheduler.start", stamp(100), proc="scheduler", pid=2, mode="daemon")
    log.emit("scheduler.error", stamp(5), proc="scheduler", pid=1, phase="stall check", error="boom")
    log.emit("scheduler.exit", stamp(50), proc="scheduler", pid=1, reason="finished: no open tasks", runs_started=2)
    log.emit("stall.nudge", stamp(6), proc="scheduler", pid=1, task="t", to="ceo", step=0)
    log.emit("agent.pause", stamp(7), proc="scheduler", pid=1, agent="ceo", reason="failures")
    log.emit("agent.failure", stamp(7), proc="scheduler", pid=1, agent="ceo", count=3)
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(500))
    assert m["scheduler"] == {"starts": 2, "errors": {"stall check": 1}, "exits": {"finished: no open tasks": 1}}
    assert m["stalls"] == 1 and m["pauses"] == {"total": 1, "by_reason": {"failures": 1}} and m["agent_failures"] == 1
    assert "stall check x1" in observe.render_metrics(m)
