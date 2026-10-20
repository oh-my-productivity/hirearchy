"""The event log (emission side): files, envelope, safety, retention, trace stamping and every emitted kind."""

import asyncio
import dataclasses
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest
import testkit

from orgmcp import telemetry
from orgmcp.cli import main
from orgmcp.core import ROOT, Org, join_frontmatter, split_frontmatter
from orgmcp.eligibility import FailureCounter
from orgmcp.eligibility.testing import MemoryFailureCounter
from orgmcp.scheduler import Scheduler
from orgmcp.scheduler.testing import ScriptedLadder
from orgmcp.stalls import StallLadder
from orgmcp.server import build_server

FAKE = str(testkit.FAKE_AGENT)
SILENT = {"echo": lambda _: None}


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    telemetry.reset()
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


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


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
    sched = Scheduler(org, fake_runner(mode), **SILENT, **kw)
    sched.acquire()
    try:
        drain(sched)
    finally:
        sched.release()
    return sched


def call(server, tool, **args):
    return asyncio.run(server.call_tool(tool, args))


class Clock:
    def __init__(self):
        self.offset = 0.0

    def __call__(self):
        return time.time() + self.offset

    def advance(self, seconds):
        self.offset += seconds


def test_the_scheduler_prunes_once_a_day_and_says_so(org):
    base = org.root / ".runtime" / "events"
    old = base / (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    old.mkdir(parents=True)
    (old / "mcp-1-1.jsonl").write_text("{}\n")
    clock = Clock()
    sched = Scheduler(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.tick()
    assert not old.exists()
    (prune,) = read_events(org, "prune")
    assert prune["removed_days"] == [old.name] and prune["proc"] == "scheduler" and prune["actor"] == "runtime"
    again = base / (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    again.mkdir()
    sched.tick()
    assert again.exists()  # not within a day
    clock.advance(86400 + 1)
    sched.tick()
    assert not again.exists()


def test_stall_notices_and_nudge_events_carry_the_task_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    clock = Clock()
    sched = Scheduler(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.acquire()
    try:
        drain(sched)
        for _ in range(3):
            clock.advance(float(org.config["stall_after"]) + 1)
            drain(sched)
    finally:
        sched.release()
    notices = [m for m in org.received("ceo") + org.received(ROOT) if m.sender == "runtime" and m.title.endswith(": T")]
    assert len(notices) == 2 and {m.trace for m in notices} == {task.id}
    nudges = read_events(org, "stall.nudge")
    assert [(n["task"], n["to"], n["step"], n["trace"]) for n in nudges] == [
        (task.id, "ceo", 0, task.id), (task.id, "root", 1, task.id)]


def test_cli_command_events(org):
    root = ["--root", str(org.root)]
    main([*root, "status"])
    with pytest.raises(SystemExit):
        main([*root, "send", "nobody", "hi"])
    ok, bad = [e for e in read_events(org, "cli.command")]
    assert (ok["command"], ok["ok"], ok["error"], ok["proc"], ok["actor"]) == ("status", True, None, "cli", "root")
    assert bad["command"] == "send" and bad["ok"] is False and "no such agent" in bad["error"]
    assert bad["error_type"] == "OrgError" and bad["ms"] >= 0


def test_cli_init_records_its_command_in_the_new_org(tmp_path):
    main(["init", str(tmp_path / "brand-new"), "--mission", "m"])
    (ev,) = read_events(Org(tmp_path / "brand-new"), "cli.command")
    assert ev["command"] == "init" and ev["ok"] is True


# ------------------------------------------------------------------------------------------------- tool.call
def agent_server(org, me="ceo"):
    return build_server(org, me)


def test_tool_calls_are_recorded_with_actor_run_and_summary(org, monkeypatch):
    monkeypatch.setenv("ORG_RUN_ID", "ceo@20260101T000000000000")
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    call(server, "whoami")
    call(server, "delegate", to="ceo/eng", title="Build it", goal="g" * 3000, acceptance="a" * 200, budget=2)
    calls = read_events(org, "tool.call")
    assert [c["tool"] for c in calls] == ["whoami", "delegate"]
    who, deleg = calls
    assert who["ok"] is True and who["error"] is None and who["error_type"] is None and who["ms"] >= 0
    assert who["proc"] == "mcp" and who["actor"] == "ceo" and who["run"] == "ceo@20260101T000000000000"
    assert who["trace"] == task.id  # the one trace of the caller's batch
    assert deleg["args"] == {"to": "ceo/eng", "title": "Build it", "budget": 2, "goal_chars": 3000, "acceptance_chars": 200}
    assert deleg["trace"] == task.id


def test_every_refusal_is_recorded_and_the_tool_still_raises_the_same(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    with pytest.raises(Exception) as info:
        call(server, "delegate", to="ceo", title="x", goal="g", acceptance="a")
    assert "direct reports" in str(info.value)
    with pytest.raises(Exception) as bad:
        call(server, "report", task_id="no-such-task", status="done", summary="s")
    assert "no task no-such-task assigned to you" in str(bad.value)
    refused = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert [c["tool"] for c in refused] == ["delegate", "report"]
    assert all(c["error_type"] == "OrgError" and c["error"] for c in refused)
    assert "you can only delegate to your direct reports" in refused[0]["error"]
    assert refused[1]["args"]["task_id"] == "no-such-task" and refused[1]["args"]["status"] == "done"


def test_a_refusal_keeps_the_trace_of_the_task_it_names(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    org.report("ceo", task.id, "done", "ok")
    with pytest.raises(Exception):
        call(agent_server(org), "report", task_id=task.id, status="done", summary="again")
    bad = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert bad[0]["trace"] == task.id and "final" in bad[0]["error"]


def test_unexpected_exceptions_are_recorded_by_class(org):
    import dataclasses

    from orgmcp.overview import OrgTree

    class BrokenTree(OrgTree):  # the tree of the status tool is the port of the runtime, not a method of the facade
        def tree(self) -> str:
            return 1 / 0

    org.runtime = dataclasses.replace(org.runtime, org_tree=BrokenTree())
    server = agent_server(org)
    with pytest.raises(Exception):
        call(server, "status")
    (bad,) = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert bad["error_type"] == "ZeroDivisionError" and "division" in bad["error"]


def test_bodies_never_reach_the_log_only_their_length(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    secret = "TOPSECRET" + "z" * 4991
    call(server, "send", to="ceo/eng", body=secret, title="t" * 200)
    call(server, "write", path="ceo/work/n.md", content=secret)
    call(server, "report", task_id=task.id, status="done", summary=secret, lessons=secret[:700], artifacts=["ceo/work/n.md"])
    sent, wrote, reported = read_events(org, "tool.call")[:3]
    assert sent["args"]["body_chars"] == 5000 and "body" not in sent["args"]
    assert len(sent["args"]["title"]) == 80 and sent["args"]["to"] == "ceo/eng"
    assert wrote["args"] == {"path": "ceo/work/n.md", "content_chars": 5000, "append": False}
    assert reported["args"]["summary_chars"] == 5000 and reported["args"]["lessons_chars"] == 700
    assert reported["args"]["artifacts"] == ["ceo/work/n.md"]
    for f in event_files(org):
        assert "TOPSECRET" not in f.read_text()


def test_a_tool_call_trace_is_that_of_the_message_it_delivered(org):
    a = org.delegate(ROOT, "ceo", "A", "g", "a", budget=8)
    b = org.delegate(ROOT, "ceo", "B", "g", "a", budget=8)
    org.begin_run("ceo")  # two traces in the batch: only the call's own effect can tell
    server = agent_server(org)
    call(server, "report", task_id=b.id, status="done", summary="ok")
    call(server, "whoami")
    report, who = read_events(org, "tool.call")
    assert report["trace"] == b.id and who["trace"] is None
    assert a.id != b.id


def test_arg_summaries_by_type():
    out = telemetry.summarize_args({
        "to": "ceo", "budget": 3, "append": True, "n": None, "blob": "x" * 500, "inputs": {"topic": "secret", "k": "v"},
        "acceptance": ["one", "two"], "tools": ["read", "write"], "artifacts": ["a.md"], "obj": object(), "name": "n" * 200,
    })
    assert out["to"] == "ceo" and out["budget"] == 3 and out["append"] is True and "n" not in out
    assert out["blob_chars"] == 500 and "blob" not in out
    assert out["inputs_keys"] == ["topic", "k"] and "secret" not in json.dumps(out)
    assert out["acceptance_n"] == 2 and out["acceptance_chars"] == 6
    assert out["tools"] == ["read", "write"] and out["artifacts"] == ["a.md"]
    assert out["obj_type"] == "object" and len(out["name"]) == 80


def test_every_tool_of_every_role_is_instrumented(org, tmp_path):
    org.define_service(ROOT, "ceo", "weekly", description="A brief.", acceptance=["Short"],
                       deliverable={"description": "one file"}, budget=4)
    servers = {
        "root": build_server(org, ROOT),
        "manager": build_server(org, "ceo"),  # also offers a service: owner tools
        "worker": build_server(org, "ceo/eng"),
    }
    seen = set()
    for who, server in servers.items():
        for tool in server._tool_manager.list_tools():
            assert hasattr(tool.fn, "__wrapped__"), f"{who}: {tool.name} is not recorded"
            seen.add(tool.name)
    for name in ("whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status",
                 "health", "services", "define_service", "request", "feedback", "revise_playbook", "create_org", "start",
                 "stop", "blueprint_example", "propose_org", "apply_org", "progress"):
        assert name in seen, name


def test_tools_keep_their_names_signatures_and_docstrings(org):
    import inspect

    tools = {t.name: t for t in build_server(org, "ceo")._tool_manager.list_tools()}
    delegate = tools["delegate"]
    assert delegate.description.startswith("Assign a task to one of your direct reports.")
    assert list(delegate.parameters["properties"]) == ["to", "title", "goal", "acceptance", "inputs", "budget", "revises"]
    assert list(inspect.signature(delegate.fn).parameters) == ["to", "title", "goal", "acceptance", "inputs", "budget", "revises"]
    assert delegate.fn.__name__ == "delegate"


def test_a_tool_added_later_is_recorded_without_extra_work(org):
    server = build_server(org, ROOT)

    @server.tool()
    def observe_stub(view: str = "now", limit: int = 5) -> str:
        """A stand-in for a tool somebody adds to the server later."""
        return f"viewed {view}"

    call(server, "observe_stub", view="trace")
    (ev,) = read_events(org, "tool.call")
    assert ev["tool"] == "observe_stub" and ev["actor"] == "root" and ev["args"] == {"view": "trace", "limit": 5}


def test_the_async_progress_tool_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    call(build_server(org, ROOT), "progress")
    (ev,) = read_events(org, "tool.call")
    assert ev["tool"] == "progress" and ev["ok"] is True and ev["actor"] == "root"


def test_a_server_without_an_organization_still_works_and_writes_nothing(tmp_path):
    target = tmp_path / "later"
    from orgmcp.server import OrgBinding

    server = build_server(OrgBinding(target), ROOT)
    assert "Setup" in str(call(server, "whoami"))
    assert not target.exists()
    call(server, "create_org", mission="a mission")
    (ev,) = [e for e in read_events(Org(target), "tool.call")]
    assert ev["tool"] == "create_org" and ev["args"] == {"mission_chars": 9}
    assert not any(".runtime/events" in line for line in (target / ".gitignore").read_text().split("\n") if line.startswith("!"))


def test_emission_failure_does_not_change_a_tool_result(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "events").write_text("blocked")
    server = build_server(org, ROOT)
    assert "ceo" in str(call(server, "status"))
    with pytest.raises(Exception) as info:
        call(server, "send", to="nobody", body="x")
    assert "no such agent" in str(info.value)


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


def test_run_events_for_a_crashing_agent_pause_and_failure_chain(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    run_all(org, "crash")
    ends = read_events(org, "run.end")
    assert len(ends) == 3 and all(e["ok"] is False and e["exit_code"] == 1 and e["error"] == "exit code 1" for e in ends)
    assert [e["count"] for e in read_events(org, "agent.failure")] == [1, 2, 3]
    (pause,) = read_events(org, "agent.pause")
    assert pause["agent"] == "ceo" and pause["reason"] == "failures"
    starts = read_events(org, "run.start")
    assert [s["budget_before"] for s in starts] == [10, 9, 8] and [e["budget_after"] for e in ends] == [9, 8, 7]
    # the notice to root about the failing agent belongs to the request
    notice = [m for m in org.received(ROOT) if m.sender == "runtime"][0]
    assert notice.trace == task.id


def test_a_run_that_times_out_is_recorded_as_killed_and_timed_out(org):
    configure(org, run_timeout=0.3)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    sched = Scheduler(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    try:
        for _ in range(100):
            sched.tick()
            if read_events(org, "run.end"):
                break
            time.sleep(0.05)
    finally:
        sched.release()
    end = read_events(org, "run.end")[0]
    assert end["ok"] is False and end["timed_out"] is True and end["killed"] is True
    assert end["exit_code"] == -9 and "timed out" in end["error"] and end["duration_ms"] >= 300


def test_a_run_interrupted_by_shutdown_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    sched = Scheduler(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    sched.tick()
    assert "ceo" in sched.runs
    sched.release()
    end = read_events(org, "run.end")[0]
    assert end["killed"] is True and end["ok"] is False and end["error"] == "interrupted by scheduler shutdown"
    assert read_events(org, "scheduler.exit")[0]["runs_started"] == 1


def test_a_run_of_an_agent_retired_mid_run_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    sched = Scheduler(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    try:
        sched.tick()
        org.retire(ROOT, "ceo", "gone")
        sched._reap()
    finally:
        sched.release()
    end = read_events(org, "run.end")[0]
    assert end["agent"] == "ceo" and end["killed"] is True and end["budget_after"] is None
    assert "retired" in end["error"]


def test_a_run_that_cannot_start_has_a_start_and_an_end(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)

    def runner(o, addr, prompt):
        return ["/nonexistent/binary"], o.dir(addr), dict(os.environ)

    sched = Scheduler(org, runner, **SILENT)
    sched.acquire()
    try:
        sched.tick()
    finally:
        sched.release()
    (start,), (end,) = read_events(org, "run.start"), read_events(org, "run.end")
    assert start["run"] == end["run"] and start["child_pid"] is None
    assert end["ok"] is False and end["error"].startswith("failed to start") and end["exit_code"] is None
    assert read_events(org, "agent.failure")[0]["count"] == 1


def test_the_run_id_reaches_the_agent_process_environment(org, tmp_path):
    out = tmp_path / "env.txt"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    cmd = ["sh", "-c", f'echo "$ORG_RUN_ID" > {out}']

    def runner(o, addr, prompt):
        env = {k: v for k, v in os.environ.items() if k != "ORG_RUN_ID"}
        return cmd, o.dir(addr), env

    sched = Scheduler(org, runner, **SILENT)
    sched.acquire()
    try:
        drain(sched)
    finally:
        sched.release()
    (start,) = read_events(org, "run.start")
    assert out.read_text().strip() == start["run"]


def test_scheduler_start_and_exit_describe_the_mode_and_reason(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    previous = signal.getsignal(signal.SIGTERM)
    try:
        Scheduler(org, fake_runner("work"), **SILENT).serve(until_done=True, max_runs=20)
    finally:
        signal.signal(signal.SIGTERM, previous)
    start, = read_events(org, "scheduler.start")
    assert start["mode"] == "until_done" and start["max_runs"] == 20 and start["max_parallel"] == 3
    assert start["version"] and start["proc"] == "scheduler" and start["actor"] == "runtime"
    exit_, = read_events(org, "scheduler.exit")
    assert exit_["reason"] == "finished: no open tasks" and exit_["runs_started"] == 3


def test_until_idle_and_once_modes(org):
    previous = signal.getsignal(signal.SIGTERM)
    try:
        Scheduler(org, fake_runner("work"), **SILENT).serve(until_idle=True)
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert read_events(org, "scheduler.start")[0]["mode"] == "until_idle"
    assert read_events(org, "scheduler.exit")[0]["reason"].startswith("idle")
    sched = Scheduler(org, fake_runner("work"), **SILENT)
    sched.mode = "once"
    sched.acquire()
    sched.release()
    assert read_events(org, "scheduler.start")[-1]["mode"] == "once"


def test_an_error_in_serve_is_the_exit_reason(org):
    class Broken(MemoryFailureCounter):
        def repair(self):
            return 1 / 0

    sched = Scheduler(org, fake_runner("work"), ports={FailureCounter: Broken()}, **SILENT)
    previous = signal.getsignal(signal.SIGTERM)
    try:
        with pytest.raises(ZeroDivisionError):
            sched.serve(until_idle=True)
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert read_events(org, "scheduler.exit")[0]["reason"].startswith("error: ZeroDivisionError")


def test_heartbeat_lists_running_runs_and_what_waits(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=4)
    org.send("ceo", ROOT, "need a decision")
    clock = Clock()
    sched = Scheduler(org, fake_runner("hang"), clock=clock, **SILENT)
    sched.acquire()
    try:
        sched.tick()
        assert len(read_events(org, "scheduler.heartbeat")) == 1
        sched.tick()
        assert len(read_events(org, "scheduler.heartbeat")) == 1  # not before heartbeat_seconds
        clock.advance(61)
        sched.tick()
        beats = read_events(org, "scheduler.heartbeat")
        assert len(beats) == 2
        (run_id,) = [r.run_id for r in sched.runs.values()]
        assert beats[-1]["running"] == [run_id] and beats[-1]["runnable"] == 0 and beats[-1]["waiting_on_you"] == 1
    finally:
        sched.release()


def test_heartbeat_interval_is_configurable(org):
    configure(org, heartbeat_seconds=5)
    clock = Clock()
    sched = Scheduler(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.tick()
    clock.advance(6)
    sched.tick()
    assert len(read_events(org, "scheduler.heartbeat")) == 2


def test_a_failing_phase_is_an_error_event_once_per_change(org):
    ladder = ScriptedLadder()
    ladder.fail = RuntimeError("kaput")
    sched = Scheduler(org, fake_runner("idle"), ports={StallLadder: ladder}, **SILENT)
    for _ in range(4):
        sched.tick()
    errors = read_events(org, "scheduler.error")
    assert len(errors) == 1
    assert errors[0]["phase"] == "stall check" and errors[0]["error"] == "RuntimeError: kaput"


def test_budget_pause_events_and_notice_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=1)
    org.start_run_log("ceo")  # the one run is already used up
    sched = Scheduler(org, fake_runner("idle"), **SILENT)
    sched.tick()
    (pause,) = read_events(org, "agent.pause")
    assert pause["agent"] == "ceo" and pause["reason"] == "budget" and pause["actor"] == "runtime"
    notice = [m for m in org.received(ROOT) if m.sender == "runtime"][0]
    assert notice.trace == task.id
    org.send(ROOT, "ceo", "more", budget=3)
    sched.tick()
    assert read_events(org, "agent.resume")[0]["reason"] == "budget is back"
    sched.release()


def test_orphan_recovery_is_recorded_with_the_run_id_of_the_dead_run(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    log = org.start_run_log("ceo")
    victim = subprocess.Popen(["sleep", "60"], start_new_session=True)
    try:
        from orgmcp.scheduler import _start_time

        org.save_ledger("running", {"ceo": {"pgid": victim.pid, "lstart": _start_time(victim.pid), "started": time.time(),
                                            "scheduler": 999999, "log": str(log.relative_to(org.root))}})
        sched = Scheduler(org, fake_runner("idle"), **SILENT)
        sched.acquire()
        sched.release()
        (orphan,) = read_events(org, "run.orphan")
        assert orphan["agent"] == "ceo" and orphan["run"] == f"ceo@{log.stem}" and orphan["action"] == "killed"
        assert orphan["detail"] and victim.wait(timeout=10) == -signal.SIGKILL
    finally:
        if victim.poll() is None:
            victim.kill()
            victim.wait()


def test_orphan_that_cannot_be_verified_is_kept(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    log = org.start_run_log("ceo")
    victim = subprocess.Popen(["sleep", "60"], start_new_session=True)
    try:
        org.save_ledger("running", {"ceo": {"pgid": victim.pid, "lstart": None, "started": time.time(),
                                            "scheduler": 999999, "log": str(log.relative_to(org.root))}})
        sched = Scheduler(org, fake_runner("idle"), **SILENT)
        sched.acquire()
        sched.tick()
        sched.release()
        orphans = read_events(org, "run.orphan")
        assert [o["action"] for o in orphans] == ["kept"]  # reported once, not on every tick
    finally:
        victim.kill()
        victim.wait()


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
            assert len(json.dumps(e).encode()) <= telemetry.LINE_MAX


def test_scheduler_runs_work_with_events_off(org):
    configure(org, events=False)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    run_all(org, "work")
    assert (org.root / "ceo/eng/work/out.md").is_file()
    assert not (org.root / ".runtime" / "events").exists()


def test_a_real_mcp_server_process_writes_its_own_events_file(org):
    """The stdio server (``orgmcp mcp``) as kiro starts it: ORG_AGENT and ORG_RUN_ID in its environment."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")

    async def session():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "orgmcp", "mcp"],
            env={**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": "ceo", "ORG_RUN_ID": "ceo@20260101T000000000000"},
        )
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                await s.call_tool("whoami", {})
                refused = await s.call_tool("send", {"to": "nobody", "body": "a secret body"})
                assert refused.isError

    asyncio.run(session())
    mcp_files = [f for f in event_files(org) if f.name.startswith("mcp-")]
    assert len(mcp_files) == 1 and f"-{os.getpid()}-" not in mcp_files[0].name
    who, bad = [json.loads(line) for line in mcp_files[0].read_text().splitlines()]
    assert (who["proc"], who["tool"], who["actor"], who["run"], who["trace"]) == ("mcp", "whoami", "ceo", "ceo@20260101T000000000000", task.id)
    assert bad["ok"] is False and bad["error"] == "no such agent: nobody" and bad["args"] == {"to": "nobody", "body_chars": 13, "title": "", "budget": 0}
    assert (who["seq"], bad["seq"]) == (1, 2) and who["pid"] != os.getpid()
