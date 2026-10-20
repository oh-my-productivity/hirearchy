import json
import os
import subprocess
import sys
import time

import pytest
import testkit

from orgmcp.cli import main
from orgmcp.core import ROOT, OrgError
from orgmcp.scheduler import Scheduler, ensure_kiro_profile, kiro_profile_name, kiro_runner

FAKE = str(testkit.FAKE_AGENT)


def fake_runner(mode="work"):
    def build(org, addr, prompt):
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}
        return [sys.executable, FAKE], org.dir(addr), env

    return build


def run_until_idle(sched, max_ticks=500):
    sched.acquire()
    try:
        for _ in range(max_ticks):
            if not sched.tick():
                return
            time.sleep(0.02)
        raise AssertionError("organization never went idle")
    finally:
        sched.release()


def test_task_flows_down_and_result_flows_up(org):
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    sched = Scheduler(org, fake_runner("work"), echo=lambda _: None)
    run_until_idle(sched)

    results = [m for m in org.received(ROOT) if m.type == "result"]
    assert len(results) == 1 and results[0].reply_to == task.id and results[0].status == "done"
    assert (org.root / "ceo/eng/work/out.md").read_text() == "done: Ship it"
    # ceo ran twice (task, then result); eng ran once
    assert org.runs_used("ceo") == 2 and org.runs_used("ceo/eng") == 1
    # eng returned its unspent run with its result, ceo (nothing else open) returned all it had left with its own
    assert results[0].budget == (6 - 2 + 1) - 2 and org.budget("ceo") == 0 and org.budget("ceo/eng") == 0
    log = subprocess.run(["git", "log", "--oneline"], cwd=org.root, capture_output=True, text=True).stdout
    assert "ceo/eng: run ok" in log


def test_crashing_agent_is_retried_then_paused(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    sched = Scheduler(org, fake_runner("crash"), echo=lambda _: None)
    run_until_idle(sched)
    assert org.paused("ceo") == "failures"
    assert org.runs_used("ceo") == 3
    assert org.unread("ceo") == 1  # the task is still there for when it is fixed
    notes = [m for m in org.messages(ROOT, "inbox") if m.sender == "runtime"]
    assert any("keeps failing" in m.title for m in notes)


def test_out_of_budget_pauses_and_notifies_parent(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=1)
    org.send(ROOT, "ceo", "also this")  # arrives later, but ceo will have no budget left
    sched = Scheduler(org, fake_runner("idle"), echo=lambda _: None)
    sched.acquire()
    sched.tick()  # ceo runs once with both messages
    while sched.runs:
        sched._reap()
    org.send(ROOT, "ceo", "one more")
    sched.tick()
    sched.release()
    assert org.paused("ceo") == "budget"
    assert any("out of budget" in m.title for m in org.messages(ROOT, "inbox"))
    # a grant unpauses it
    org.send(ROOT, "ceo", "here are more runs", budget=2)
    assert "ceo" in sched._runnable()


class Clock:
    """Real time plus an offset, so tests can move time forward (run logs carry real mtimes)."""

    def __init__(self):
        self.offset = 0.0

    def __call__(self):
        return time.time() + self.offset

    def advance(self, seconds):
        self.offset += seconds


def stall_sched(org, runner=None):
    clock = Clock()
    return Scheduler(org, runner or fake_runner("idle"), echo=lambda _: None, clock=clock), clock


def after_stall(org, clock, sched):
    """Let `stall_after` pass, then run the scheduler until it is idle again."""
    clock.advance(float(org.config["stall_after"]) + 1)
    run_until_idle(sched)


def titles(org, addr):
    return [m.title for m in org.received(addr) if m.sender == "runtime"]


def ledger(org):
    return json.loads((org.root / ".runtime/nudges.json").read_text())


def eng_is_stuck(org):
    """root -> ceo (task already read) -> eng (task from ceo); the agents will do nothing."""
    root_task = org.delegate(ROOT, "ceo", "Ship", "g", "a", budget=10)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    return root_task, org.delegate("ceo", "ceo/eng", "Build", "g", "a", budget=4)


def test_stalled_task_is_nudged_then_escalated(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    sched, clock = stall_sched(org)
    run_until_idle(sched)
    assert not (org.root / ".runtime/nudges.json").exists()  # nothing is stalled before stall_after
    clock.advance(float(org.config["stall_after"]) / 2)
    run_until_idle(sched)
    assert not (org.root / ".runtime/nudges.json").exists()

    after_stall(org, clock, sched)
    assert ledger(org)[task.id]["step"] == 0
    assert titles(org, "ceo") == ["reminder: T"] and titles(org, ROOT) == []

    after_stall(org, clock, sched)  # the assigner (root) hears about it
    assert ledger(org)[task.id]["step"] == 1
    assert titles(org, ROOT) == ["stalled: T"]

    after_stall(org, clock, sched)  # root was the last step: the ladder stops
    assert titles(org, "ceo") == ["reminder: T"] and titles(org, ROOT) == ["stalled: T"]


def test_stall_ladder_climbs_to_root_and_stops(org):
    root_task, task = eng_is_stuck(org)
    sched, clock = stall_sched(org)
    run_until_idle(sched)
    assert titles(org, "ceo/eng") == []

    after_stall(org, clock, sched)  # step 0: the assignee
    assert titles(org, "ceo/eng") == ["reminder: Build"] and titles(org, "ceo") == []
    after_stall(org, clock, sched)  # step 1: the assigner
    assert titles(org, "ceo") == ["stalled: Build"] and titles(org, ROOT) == []
    after_stall(org, clock, sched)  # step 2: next ancestor, which is root
    assert titles(org, ROOT) == ["stalled: Build"]
    note = next(m for m in org.received(ROOT) if m.sender == "runtime")
    assert "`ceo/eng`" in note.body and "`ceo`" in note.body
    assert ledger(org)[task.id]["step"] == 2

    for _ in range(2):  # root has been told: nothing more, no matter how long it takes
        after_stall(org, clock, sched)
    assert titles(org, "ceo/eng") == ["reminder: Build"]
    assert titles(org, "ceo") == ["stalled: Build"] and titles(org, ROOT) == ["stalled: Build"]
    assert ledger(org)[task.id]["step"] == 2
    assert root_task.id not in ledger(org)  # ceo is waiting on eng, so it never stalls


def test_no_nudge_while_waiting_on_a_delegation(org):
    root_task, _ = eng_is_stuck(org)
    sched, clock = stall_sched(org)
    run_until_idle(sched)
    after_stall(org, clock, sched)
    assert org.outstanding("ceo") and not any(t.startswith("reminder") for t in titles(org, "ceo"))
    assert root_task.id not in ledger(org)


def test_stall_is_detected_while_another_agent_is_running(org):
    eng_is_stuck(org)
    org.hire("ceo", "ops", "Operations", "Keep the lights on.")
    org.send(ROOT, "ceo/ops", "stay busy", budget=2)

    def runner(o, addr, prompt):
        if addr == "ceo/ops":
            return [sys.executable, "-c", "import time; time.sleep(60)"], o.dir(addr), dict(os.environ)
        return fake_runner("idle")(o, addr, prompt)

    sched, clock = stall_sched(org, runner)
    sched.acquire()
    try:
        for _ in range(200):
            sched.tick()
            if "ceo/eng" not in sched.runs and org.runs_used("ceo/eng") == 1:
                break
            time.sleep(0.02)
        assert "ceo/ops" in sched.runs and titles(org, "ceo/eng") == []
        clock.advance(float(org.config["stall_after"]) + 1)
        sched.tick()
        assert "ceo/ops" in sched.runs  # still busy elsewhere, yet eng got its reminder
        assert titles(org, "ceo/eng") == ["reminder: Build"]
    finally:
        sched.release()


def test_ladder_state_is_dropped_when_the_task_closes(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    sched, clock = stall_sched(org)
    run_until_idle(sched)
    after_stall(org, clock, sched)
    assert task.id in ledger(org)
    org.report("ceo", task.id, "done", "finally")
    run_until_idle(sched)
    assert ledger(org) == {}


def failures(org):
    return json.loads((org.root / ".runtime/failures.json").read_text())


def test_failure_count_survives_a_scheduler_restart(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    first = Scheduler(org, fake_runner("crash"), echo=lambda _: None)
    first.acquire()
    try:
        for _ in range(500):
            first.tick(max_runs=2)
            if org.runs_used("ceo") == 2 and not first.runs:
                break
            time.sleep(0.02)
    finally:
        first.release()
    assert failures(org) == {"ceo": 2} and org.paused("ceo") is None

    run_until_idle(Scheduler(org, fake_runner("crash"), echo=lambda _: None))  # a fresh process: 3rd strike
    assert org.paused("ceo") == "failures" and org.runs_used("ceo") == 3


def test_failure_count_resets_on_success(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.save_ledger("failures", {"ceo": 2, "ceo/eng": 1})
    run_until_idle(Scheduler(org, fake_runner("idle"), echo=lambda _: None))
    assert failures(org) == {"ceo/eng": 1}
    assert org.paused("ceo") is None


def test_resume_resets_the_failure_count(org):
    org.save_ledger("failures", {"ceo": 3, "ceo/eng": 1})
    org.pause("ceo", "failures")
    main(["--root", str(org.root), "resume", "ceo"])
    assert org.paused("ceo") is None and failures(org) == {"ceo/eng": 1}


def test_single_scheduler_per_org(org):
    a = Scheduler(org, fake_runner(), echo=lambda _: None)
    a.acquire()
    with pytest.raises(OrgError, match="already running"):
        Scheduler(org, fake_runner(), echo=lambda _: None).acquire()
    a.release()


def test_kiro_runner_builds_isolated_command(org, tmp_path, monkeypatch):
    monkeypatch.setattr("orgmcp.scheduler.KIRO_AGENTS_DIR", tmp_path / "agents")
    monkeypatch.setattr("orgmcp.scheduler.ensure_kiro_profile",
                        lambda tools, org: ensure_kiro_profile(tools, tmp_path / "agents", org=org))
    org.write(ROOT, "ceo/AGENT.md", "---\nrole: CEO\nmodel: claude-haiku-4.5\ntools: [read]\n---\nLead.\n")
    cmd, cwd, env = kiro_runner()(org, "ceo", "PROMPT")
    name = kiro_profile_name(org.root, ["read"])
    assert cmd[:5] == ["kiro-cli", "chat", "--no-interactive", "--agent", name]
    assert cmd[-2:] == ["--model", "claude-haiku-4.5"] and "PROMPT" not in cmd  # the prompt goes via stdin
    assert cwd == org.dir("ceo") and env["ORG_AGENT"] == "ceo" and env["ORG_ROOT"] == str(org.root)
    profile = json.loads((tmp_path / "agents" / f"{name}.json").read_text())
    assert profile["includeMcpJson"] is False  # no gmail/whatsapp/etc. inside the org
    assert profile["tools"] == ["@orgmcp", "read"] and "orgmcp" in profile["mcpServers"]
