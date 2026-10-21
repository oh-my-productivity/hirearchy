import json
import os
import re
import shutil
import sys
import time

import pytest
import testkit
from testkit.reach.hirearchy.app import wiring
from testkit.scheduler_loop import loop_over

from hirearchy.core import ROOT
from hirearchy.eventlog import LINE_MAX

FAKE = str(testkit.FAKE_AGENT)
SILENT = {"echo": lambda _: None}


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    wiring.process_resources().reset()  # forget the open event files and counters of the process
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def read_events(org, kind=None):
    """Every event of the org, merged by time (the way a reader would)."""
    out = []
    for f in event_files(org):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))  # every line is a valid JSON object
    out.sort(key=lambda e: (e["ts"], e["seq"]))
    return [e for e in out if kind is None or e["kind"] == kind]


def fake_runner(mode="work"):
    def build(org, addr, prompt):
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}
        return [sys.executable, FAKE], org.dir(addr), env

    return build


def drain(sched, limit=60.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.02)
    assert time.time() < deadline, "organization never went idle"


def run_all(org, mode="work", **kw):
    sched = loop_over(org, fake_runner(mode), **SILENT, **kw)
    sched.acquire()
    try:
        drain(sched)
    finally:
        sched.release()
    return sched


# ------------------------------------------------------------------------------- scheduler: runs, through tools
def test_a_real_run_shows_start_end_tool_calls_and_traces(org):
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=8)
    run_all(org, "tools")
    starts, ends = read_events(org, "run.start"), read_events(org, "run.end")
    assert len(starts) == len(ends) == org.runs_used("ceo") + org.runs_used("ceo/eng") == 3
    assert {s["run"] for s in starts} == {e["run"] for e in ends}
    for s in starts:
        assert re.fullmatch(r"ceo(/eng)?@\d{8}T\d{12}", s["run"]) and s["run"].split("@")[0] == s["agent"]
        assert s["traces"] == [task.id] and s["trace"] == task.id and s["batch"] and s["child_pid"] == s["pgid"] > 0
        assert s["pid"] == os.getpid()  # the envelope pid is the scheduler's own
        assert s["proc"] == "scheduler" and s["actor"] == "runtime" and s["budget_before"] >= 1
        assert (org.dir(s["agent"]) / "runs" / f"{s['run'].split('@')[1]}.log").is_file()
    for e in ends:
        assert e["ok"] is True and e["exit_code"] == 0 and e["duration_ms"] > 0 and e["timed_out"] is False
        assert e["killed"] is False and e["error"] is None and e["trace"] == task.id
    eng = next(e for e in ends if e["agent"] == "ceo/eng")
    eng_start = next(s for s in starts if s["agent"] == "ceo/eng")
    assert eng["budget_after"] == org.budget("ceo/eng") == 0 and eng_start["budget_before"] == 2
    # the MCP-side events of those runs carry the run id and the actor
    calls = read_events(org, "tool.call")
    assert calls and {c["proc"] for c in calls} == {"mcp"}
    by_run = {}
    for c in calls:
        by_run.setdefault(c["run"], []).append(c)
    assert set(by_run) == {s["run"] for s in starts}
    for run_id, cs in by_run.items():
        assert {c["actor"] for c in cs} == {run_id.split("@")[0]}
        assert {c["trace"] for c in cs} == {task.id}
    leaf = by_run[eng_start["run"]]
    refused = [c for c in leaf if not c["ok"]]
    assert [c["tool"] for c in refused] == ["report"] and "status must be one of" in refused[0]["error"]
    assert refused[0]["args"]["summary_chars"] == 5000
    assert [c["tool"] for c in leaf if c["ok"]] == ["whoami", "write", "report"]
    # messages: every one is stamped with the trace and delivered by the agent that sent it
    delivered = read_events(org, "msg.deliver")
    assert {d["trace"] for d in delivered} == {task.id}
    assert {d["actor"] for d in delivered} == {"root", "ceo", "ceo/eng"}
    # scheduler lifecycle
    lifecycle = [e["kind"] for e in read_events(org) if e["kind"] in ("scheduler.start", "scheduler.exit")]
    assert lifecycle == ["scheduler.start", "scheduler.exit"] and read_events(org, "scheduler.heartbeat")


def test_runs_counted_in_events_match_the_run_logs(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    run_all(org, "work")
    logs = {f"{a}@{p.stem}" for a in ("ceo", "ceo/eng") for p in (org.dir(a) / "runs").glob("*.log")}
    assert {s["run"] for s in read_events(org, "run.start")} == logs == {e["run"] for e in read_events(org, "run.end")}


def test_every_line_of_a_full_run_is_valid_and_gapless(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    run_all(org, "tools")
    for f in event_files(org):
        events = [json.loads(line) for line in f.read_text().splitlines()]
        assert [e["seq"] for e in events] == list(range(1, len(events) + 1)), f.name
        assert {e["v"] for e in events} == {1}
        for e in events:
            assert {"ts", "proc", "pid", "kind", "actor", "run", "trace"} <= set(e)
            assert len(json.dumps(e).encode()) <= LINE_MAX
