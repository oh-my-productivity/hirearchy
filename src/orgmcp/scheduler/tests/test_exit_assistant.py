# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import os
import sys
import time

import pytest
import testkit
from testkit.legacy.orgmcp.core import ROOT

from orgmcp import scheduler as sched_mod
from orgmcp.scheduler import EXIT_FILE, Scheduler, describe_scheduler, nothing_to_do

FAKE = str(testkit.FAKE_AGENT)


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    (work / "<folder-with-your-files>").mkdir(parents=True)  # the documents example's input folder
    (work / "<folder-with-your-data>").mkdir()  # the analysis example's input folder
    monkeypatch.chdir(work)
    return work


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


# ------------------------------------------------------------------------------------ until done
def fake_runner(mode="work"):
    def build(o, addr, prompt):
        return [sys.executable, FAKE], o.dir(addr), {**os.environ, "ORG_ROOT": str(o.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    return build


def test_until_done_exits_when_root_has_no_open_task(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    lines = []
    Scheduler(org, fake_runner("work"), echo=lines.append).serve(until_done=True)
    assert "scheduler exiting: finished: no open tasks" in lines and not org.outstanding(ROOT)
    assert (org.root / EXIT_FILE).read_text().strip() == "finished: no open tasks"
    assert describe_scheduler(org) == "scheduler: stopped (finished: no open tasks)"
    assert not (org.root / ".runtime" / "scheduler.pid").exists()


def test_a_new_scheduler_forgets_the_old_exit_reason(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    Scheduler(org, fake_runner("work"), echo=lambda _: None).serve(until_done=True)
    assert (org.root / EXIT_FILE).exists()
    sched = Scheduler(org, fake_runner("work"), echo=lambda _: None)
    sched.acquire()
    try:
        assert not (org.root / EXIT_FILE).exists()
    finally:
        sched.release()


def test_until_done_keeps_going_while_a_task_is_open_or_work_is_runnable(org):
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    sched = Scheduler(org, fake_runner("idle"), echo=lambda _: None)
    assert not sched.finished()  # ceo has unread work
    sched.acquire()
    try:
        deadline = time.time() + 20
        while org.unread("ceo") and time.time() < deadline:
            sched.tick()
            time.sleep(0.05)
        while sched.runs and time.time() < deadline:
            sched._reap()
            time.sleep(0.05)
    finally:
        sched.release()
    assert org.unread("ceo") == 0 and org.outstanding(ROOT)  # read it, never reported: still open
    assert not sched.finished() and not nothing_to_do(org)
    org.report("ceo", task.id, "done", "ok")
    assert sched.finished() and nothing_to_do(org)


def test_work_still_runnable_keeps_an_until_done_scheduler_alive(org):
    org.send(ROOT, "ceo", "a note with no task", budget=2)
    assert not org.outstanding(ROOT) and not nothing_to_do(org)  # nothing open for root, but ceo has mail
    assert not Scheduler(org, echo=lambda _: None).finished()
    assert Scheduler(org, echo=lambda _: None).finished(max_runs=0)  # ...unless the run cap forbids starting it


def test_until_done_does_not_exit_early_when_the_run_cap_blocks_open_work(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    assert not Scheduler(org, echo=lambda _: None).finished(max_runs=0)  # root still has an open task


def test_a_real_until_done_scheduler_process_exits_by_itself(org, monkeypatch):
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    org.begin_run("ceo")
    org.report("ceo", org.outstanding(ROOT)[0].id, "done", "ok")  # already done, but ceo still has the task result to read
    org.end_run("ceo", ok=True)
    pid = sched_mod.start_scheduler(org, max_runs=0, until_done=True)
    deadline = time.time() + 20
    while sched_mod.scheduler_state(org).state != "stopped" and time.time() < deadline:
        time.sleep(0.1)
    assert sched_mod.scheduler_state(org).state == "stopped"
    log = (org.root / ".runtime" / "scheduler.log").read_text()
    assert "--until-done" in log and "scheduler exiting: finished: no open tasks" in log and pid > 0
    assert describe_scheduler(org) == "scheduler: stopped (finished: no open tasks)"
