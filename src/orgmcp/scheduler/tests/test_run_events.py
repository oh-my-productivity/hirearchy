# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json
import os
import shutil
import signal
import subprocess
import sys
import time

import pytest
import testkit
from testkit.legacy.orgmcp.app import wiring
from testkit.legacy.orgmcp.core import ROOT, join_frontmatter, split_frontmatter
from testkit.scheduler_loop import loop_over

from orgmcp.eligibility import FailureCounter
from orgmcp.eligibility.testing import MemoryFailureCounter
from orgmcp.scheduler.testing import ScriptedLadder
from orgmcp.stalls import StallLadder

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
    sched = loop_over(org, fake_runner(mode), **SILENT, **kw)
    sched.acquire()
    try:
        drain(sched)
    finally:
        sched.release()
    return sched


class Clock:
    def __init__(self):
        self.offset = 0.0

    def __call__(self):
        return time.time() + self.offset

    def advance(self, seconds):
        self.offset += seconds


def test_stall_notices_and_nudge_events_carry_the_task_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    clock = Clock()
    sched = loop_over(org, fake_runner("idle"), clock=clock, **SILENT)
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
    sched = loop_over(org, fake_runner("hang"), **SILENT)
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
    sched = loop_over(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    sched.tick()
    assert "ceo" in sched.state.runs
    sched.release()
    end = read_events(org, "run.end")[0]
    assert end["killed"] is True and end["ok"] is False and end["error"] == "interrupted by scheduler shutdown"
    assert read_events(org, "scheduler.exit")[0]["runs_started"] == 1


def test_a_run_of_an_agent_retired_mid_run_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    sched = loop_over(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    try:
        sched.tick()
        org.retire(ROOT, "ceo", "gone")
        sched.reap()
    finally:
        sched.release()
    end = read_events(org, "run.end")[0]
    assert end["agent"] == "ceo" and end["killed"] is True and end["budget_after"] is None
    assert "retired" in end["error"]


def test_a_run_that_cannot_start_has_a_start_and_an_end(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)

    def runner(o, addr, prompt):
        return ["/nonexistent/binary"], o.dir(addr), dict(os.environ)

    sched = loop_over(org, runner, **SILENT)
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

    sched = loop_over(org, runner, **SILENT)
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
        loop_over(org, fake_runner("work"), **SILENT).serve(until_done=True, max_runs=20)
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
        loop_over(org, fake_runner("work"), **SILENT).serve(until_idle=True)
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert read_events(org, "scheduler.start")[0]["mode"] == "until_idle"
    assert read_events(org, "scheduler.exit")[0]["reason"].startswith("idle")
    sched = loop_over(org, fake_runner("work"), **SILENT)
    sched.state.mode = "once"
    sched.acquire()
    sched.release()
    assert read_events(org, "scheduler.start")[-1]["mode"] == "once"


def test_an_error_in_serve_is_the_exit_reason(org):
    class Broken(MemoryFailureCounter):
        def repair(self):
            return 1 / 0

    sched = loop_over(org, fake_runner("work"), overrides={FailureCounter: Broken()}, **SILENT)
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
    sched = loop_over(org, fake_runner("hang"), clock=clock, **SILENT)
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
        (run_id,) = [r.run_id for r in sched.state.runs.values()]
        assert beats[-1]["running"] == [run_id] and beats[-1]["runnable"] == 0 and beats[-1]["waiting_on_you"] == 1
    finally:
        sched.release()


def test_heartbeat_interval_is_configurable(org):
    configure(org, heartbeat_seconds=5)
    clock = Clock()
    sched = loop_over(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.tick()
    clock.advance(6)
    sched.tick()
    assert len(read_events(org, "scheduler.heartbeat")) == 2


def test_a_failing_phase_is_an_error_event_once_per_change(org):
    ladder = ScriptedLadder()
    ladder.fail = RuntimeError("kaput")
    sched = loop_over(org, fake_runner("idle"), overrides={StallLadder: ladder}, **SILENT)
    for _ in range(4):
        sched.tick()
    errors = read_events(org, "scheduler.error")
    assert len(errors) == 1
    assert errors[0]["phase"] == "stall check" and errors[0]["error"] == "RuntimeError: kaput"


def test_budget_pause_events_and_notice_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=1)
    org.start_run_log("ceo")  # the one run is already used up
    sched = loop_over(org, fake_runner("idle"), **SILENT)
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
        org.save_ledger("running", {"ceo": {"pgid": victim.pid, "lstart": org.runtime.process_inspector.start_time(victim.pid), "started": time.time(),
                                            "scheduler": 999999, "log": str(log.relative_to(org.root))}})
        sched = loop_over(org, fake_runner("idle"), **SILENT)
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
        sched = loop_over(org, fake_runner("idle"), **SILENT)
        sched.acquire()
        sched.tick()
        sched.release()
        orphans = read_events(org, "run.orphan")
        assert [o["action"] for o in orphans] == ["kept"]  # reported once, not on every tick
    finally:
        victim.kill()
        victim.wait()


def test_scheduler_runs_work_with_events_off(org):
    configure(org, events=False)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    run_all(org, "work")
    assert (org.root / "ceo/eng/work/out.md").is_file()
    assert not (org.root / ".runtime" / "events").exists()
