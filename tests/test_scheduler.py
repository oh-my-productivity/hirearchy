import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from orgmcp.core import ROOT, OrgError
from orgmcp.scheduler import Scheduler, ensure_kiro_profile, kiro_runner

FAKE = str(Path(__file__).with_name("fake_agent.py"))


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
    assert org.budget("ceo") == 6 - 2 - 2 and org.budget("ceo/eng") == 2 - 1
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


def test_stalled_task_is_nudged_then_escalated(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    sched = Scheduler(org, fake_runner("idle"), echo=lambda _: None)
    run_until_idle(sched)
    nudges = json.loads((org.root / ".runtime/nudges.json").read_text())
    assert nudges[task.id] == "escalated"
    assert any(m.title.startswith("reminder") for m in org.received("ceo"))
    assert any(m.title.startswith("stalled") for m in org.received(ROOT))


def test_single_scheduler_per_org(org):
    a = Scheduler(org, fake_runner(), echo=lambda _: None)
    a.acquire()
    with pytest.raises(OrgError, match="already running"):
        Scheduler(org, fake_runner(), echo=lambda _: None).acquire()
    a.release()


def test_kiro_runner_builds_isolated_command(org, tmp_path, monkeypatch):
    monkeypatch.setattr("orgmcp.scheduler.KIRO_AGENTS_DIR", tmp_path / "agents")
    monkeypatch.setattr("orgmcp.scheduler.ensure_kiro_profile",
                        lambda tools: ensure_kiro_profile(tools, tmp_path / "agents"))
    org.write(ROOT, "ceo/AGENT.md", "---\nrole: CEO\nmodel: claude-haiku-4.5\ntools: [read]\n---\nLead.\n")
    cmd, cwd, env = kiro_runner()(org, "ceo", "PROMPT")
    assert cmd[:5] == ["kiro-cli", "chat", "--no-interactive", "--agent", "orgmcp-read"]
    assert cmd[-3:] == ["--model", "claude-haiku-4.5", "PROMPT"]
    assert cwd == org.dir("ceo") and env["ORG_AGENT"] == "ceo" and env["ORG_ROOT"] == str(org.root)
    profile = json.loads((tmp_path / "agents/orgmcp-read.json").read_text())
    assert profile["includeMcpJson"] is False  # no gmail/whatsapp/etc. inside the org
    assert profile["tools"] == ["@orgmcp", "read"] and "orgmcp" in profile["mcpServers"]
