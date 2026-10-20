# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import os
import time

from testkit.legacy.orgmcp.core import ROOT

from testkit.scheduler_loop import loop_over


def run_to_idle(sched, limit=5.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.01)


# ------------------------------------------------- QA-16: process groups
def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_for_pid(pidfile, limit=5.0):
    deadline = time.time() + limit
    while time.time() < deadline:
        if pidfile.exists() and pidfile.read_text().strip():
            return int(pidfile.read_text())
        time.sleep(0.02)
    raise AssertionError("child never started")


def spawn_tree(org, tmp_path, marker):
    pidfile = tmp_path / f"{marker}.pid"
    cmd = ["sh", "-c", f"sleep {marker} & echo $! > {pidfile}; wait"]
    sched = loop_over(org, lambda o, a, p: (cmd, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    sched.tick()
    return sched, wait_for_pid(pidfile)


def test_shutdown_kills_the_whole_process_group(org, tmp_path):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched, child = spawn_tree(org, tmp_path, "46")
    try:
        sched.release()
        time.sleep(0.2)
        assert not alive(child), "tool subprocess outlived the scheduler"
    finally:
        if alive(child):
            os.kill(child, 9)


def test_retiring_an_agent_mid_run_kills_its_process_group(org, tmp_path):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched, child = spawn_tree(org, tmp_path, "45")
    try:
        org.retire(ROOT, "ceo", "gone")
        sched.reap()
        time.sleep(0.2)
        assert sched.state.runs == {} and not alive(child) and not (org.root / "ceo").exists()
    finally:
        sched.release()
        if alive(child):
            os.kill(child, 9)


def test_runs_are_started_in_their_own_session(org, tmp_path):
    out = tmp_path / "ids.txt"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    cmd = ["sh", "-c", f"ps -o pid=,pgid= -p $$ > {out}"]
    sched = loop_over(org, lambda o, a, p: (cmd, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    pid, pgid = map(int, out.read_text().split())
    assert pid == pgid != os.getpgid(0)
