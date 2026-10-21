# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
import os
import signal
import subprocess
import time

import pytest
from testkit.reach.hirearchy.core import ROOT

from testkit.scheduler_loop import loop_over, runnable_of

SILENT = dict(echo=lambda _: None)


@pytest.fixture
def spawn():
    procs = []

    def start(own_session=True):
        p = subprocess.Popen(["sleep", "60"], start_new_session=own_session)
        procs.append(p)
        return p

    yield start
    for p in procs:
        if p.poll() is None:
            p.kill()
        p.wait()


def crash_mid_run(org, addr="ceo"):
    """What a hard-killed scheduler leaves: the batch in inflight/, the run's log (it consumed a run)."""
    org.delegate(ROOT, addr, "T", "g", "a", budget=5)
    org.begin_run(addr)
    return org.start_run_log(addr)


def record(org, addr, proc, log=None, **override):
    rec = {"pgid": proc.pid, "lstart": org.runtime.process_inspector.start_time(proc.pid), "started": time.time(), "scheduler": 999999,
           "log": str(log.relative_to(org.root)) if log else ""}
    org.save_ledger("running", {addr: {**rec, **override}})


def alive(proc):
    return proc.poll() is None


def counting_runner(prompts):
    def runner(org, addr, prompt):
        prompts.append(addr)
        return ["true"], org.dir(addr), dict(os.environ)

    return runner


def drain(sched, ticks=100):
    for _ in range(ticks):
        if not sched.tick():
            return
        time.sleep(0.02)


def test_orphan_process_group_is_killed_on_start_and_the_batch_redelivered_once(org, spawn):
    log = crash_mid_run(org)
    orphan = spawn()
    record(org, "ceo", orphan, log)
    assert org.running("ceo") and org.unread("ceo") == 0
    runs = []
    sched = loop_over(org, counting_runner(runs), **SILENT)
    sched.acquire()
    try:
        assert orphan.wait(timeout=10) == -signal.SIGKILL  # dead before anything is redelivered
        assert not org.running("ceo") and org.unread("ceo") == 1
        assert org.ledger("running") == {}
        assert "orphaned run of a scheduler that died" in log.read_text()
        drain(sched)
    finally:
        sched.release()
    assert runs == ["ceo"]  # the batch ran once, after the orphan was gone
    assert org.messages("ceo", "inbox") == [] and len(org.messages("ceo", "read")) == 1
    assert org.runs_used("ceo") == 2


def test_the_whole_orphan_process_group_dies_with_its_leader(org):
    log = crash_mid_run(org)
    # a shell leading its own session, with a child that would outlive a plain kill of the leader
    leader = subprocess.Popen(["sh", "-c", "sleep 60 & sleep 60; wait"], start_new_session=True)
    try:
        time.sleep(0.3)
        record(org, "ceo", leader, log)
        group = subprocess.run(["pgrep", "-g", str(leader.pid)], capture_output=True, text=True).stdout.split()
        assert len(group) >= 2
        loop_over(org, counting_runner([]), **SILENT).acquire()
        leader.wait(timeout=10)
        time.sleep(0.2)
        assert subprocess.run(["pgrep", "-g", str(leader.pid)], capture_output=True, text=True).stdout.split() == []
    finally:
        leader.kill()
        leader.wait()


def test_a_recorded_pid_that_is_not_a_session_leader_is_not_killed(org, spawn):
    log = crash_mid_run(org)
    bystander = spawn(own_session=False)  # same process group as the test run itself
    record(org, "ceo", bystander, log)
    assert org.runtime.orphan_judge.judge(org.ledger("running")["ceo"]) == "foreign"
    sched = loop_over(org, counting_runner([]), **SILENT)
    sched.acquire()
    try:
        assert alive(bystander)
        assert org.ledger("running") == {} and "ceo" not in sched.state.blocked
        assert org.unread("ceo") == 1  # the batch is still redelivered: our run is gone
    finally:
        sched.release()


def test_a_recorded_pid_reused_by_another_process_is_not_killed(org, spawn):
    log = crash_mid_run(org)
    stranger = spawn()  # a session leader, but not started when the recorded run was
    record(org, "ceo", stranger, log, lstart="Mon Jan  1 00:00:00 2001")
    sched = loop_over(org, counting_runner([]), **SILENT)
    sched.acquire()
    try:
        assert alive(stranger) and org.ledger("running") == {} and org.unread("ceo") == 1
    finally:
        sched.release()


@pytest.mark.parametrize("pgid", [0, 1, -5, os.getpid(), None, "x", True, 4_000_000])
def test_nonsense_records_never_kill_anything(org, pgid):
    crash_mid_run(org)
    org.save_ledger("running", {"ceo": {"pgid": pgid, "lstart": "x"}, "gone/agent": "junk"})
    sched = loop_over(org, counting_runner([]), **SILENT)
    sched.acquire()
    sched.release()
    assert org.ledger("running") == {}


def test_an_unverifiable_live_orphan_blocks_its_agent_until_it_is_gone(org, spawn):
    log = crash_mid_run(org)
    orphan = spawn()
    record(org, "ceo", orphan, log, lstart=None)  # cannot tell it is ours: in doubt
    runs = []
    messages = []
    sched = loop_over(org, counting_runner(runs), echo=messages.append)
    sched.acquire()
    try:
        for _ in range(5):
            sched.tick()
        assert alive(orphan) and runs == [] and "ceo" in sched.state.blocked
        assert org.unread("ceo") == 1 and "ceo" not in runnable_of(org, sched)
        assert any("no new run until it is gone" in m for m in messages)
        orphan.kill()
        orphan.wait()
        drain(sched)
    finally:
        sched.release()
    assert runs == ["ceo"] and not sched.state.blocked and org.ledger("running") == {}


def test_a_scheduled_run_is_recorded_while_it_lives_and_cleaned_when_reaped(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    seen = []

    def runner(o, a, p):
        return ["sleep", "0.4"], o.dir(a), dict(os.environ)

    sched = loop_over(org, runner, **SILENT)
    sched.acquire()
    try:
        sched.tick()
        rec = org.ledger("running")["ceo"]
        run = sched.state.runs["ceo"]
        assert rec["pgid"] == run.proc.pid and rec["scheduler"] == os.getpid() and rec["lstart"]
        assert org.runtime.orphan_judge.judge(rec) == "ours"
        seen.append(rec)
        drain(sched)
    finally:
        sched.release()
    assert seen and org.ledger("running") == {}
    assert ".runtime/running.json" in (org.root / ".gitignore").read_text().split()
    assert json.loads((org.root / ".runtime" / "running.json").read_text()) == {}
