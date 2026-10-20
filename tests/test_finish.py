"""Finishing and naming: until-done exit when the user must act, the plan's failure policy and sentence-safe lines,
orgmcp vs built-in tool names in the prompts, stray org files in a workspace, and the skill/instruction rules."""

import asyncio
import dataclasses
import os
import sys
import time

import pytest

from orgmcp.core import ROOT, Org
from orgmcp.scheduler import EXIT_FILE, Scheduler, describe_scheduler, waiting_on_user
from orgmcp.scheduler._exit import GraceWait
from orgmcp.scheduler._legacy import FunctionClock
from orgmcp.scheduler._ports import Console
from orgmcp.scheduler._run import GraceMemory, Standing
from orgmcp.scheduler._work import QueriedWork
from orgmcp.server import ROOT_INSTRUCTIONS, build_server, resolve_binding
from orgmcp.strays import StrayProbe


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


class Clock:
    """A fake clock for the scheduler: moves only when told (or by ``step`` on every reading)."""

    def __init__(self, step: float = 0.0):
        self.t, self.step = time.time(), step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def never_runner(org, addr, prompt):
    raise AssertionError(f"{addr} must not be started")


class Waiting:
    """The grace period of an until-done scheduler (what ``Scheduler._check_waiting`` was): ``waiting()`` is the exit reason once nothing has progressed
    without the user for ``until_done_grace_seconds``, else ''; ``waiting.since`` is when the count began. It looks at the scheduler's own runs, its blocked
    agents and its clock, over the ports of the org's runtime."""

    def __init__(self, sched):
        rt = sched.org.runtime
        self.sched, self.memory = sched, GraceMemory()
        console = type("Console", (Console,), {"say": lambda _, line: sched.echo(line)})()
        work = QueriedWork(rt.open_work, rt.runnable_query, rt.waiting_on_user)
        self.grace = GraceWait(work, rt.settings, FunctionClock(lambda: sched.clock()), console, self.memory)

    @property
    def since(self):
        return self.memory.since

    def __call__(self, max_runs=None):
        s = self.sched
        return self.grace.check(Standing(s.runs, s._blocked, max_runs is None or s.total_runs < max_runs))


# ------------------------------------------------------------------------------- until-done: waiting on the user
@pytest.fixture
def stalled_on_budget(org):
    """root's only task sits with ceo, which has used its single run: the task is unread and cannot be served."""
    task = org.delegate(ROOT, "ceo", "Rework the report", "Fix it", "It is fixed", budget=1)
    org.start_run_log("ceo")  # the one run is gone
    assert org.budget("ceo") == 0 and org.unread("ceo") == 1
    return task


def test_grace_period_with_a_fake_clock(org, stalled_on_budget):
    clock, lines = Clock(), []
    sched = Scheduler(org, never_runner, echo=lines.append, clock=clock)
    waiting = Waiting(sched)
    assert waiting() == ""  # first sight: the count starts
    assert any("Exiting in 300s unless something changes" in x for x in lines)
    clock.t += 299
    assert waiting() == ""
    clock.t += 1
    assert waiting() == 'waiting on you: "Rework the report" needs budget (ceo out of runs)'


def test_a_change_restarts_the_grace_period(org, stalled_on_budget):
    clock = Clock()
    waiting = Waiting(Scheduler(org, never_runner, echo=lambda _: None, clock=clock))
    waiting()
    clock.t += 250
    org.send(ROOT, "ceo", "more", budget=1)  # the user acts: runnable
    assert waiting() == "" and waiting.since is None
    org.start_run_log("ceo")  # ...and it is stuck again
    clock.t += 100
    assert waiting() == "" and waiting.since is not None
    clock.t += 299
    assert waiting() == ""
    clock.t += 2
    assert waiting().startswith("waiting on you:")


def test_the_grace_is_configurable(tmp_path):
    o = Org.init(tmp_path / "o", "m", {"until_done_grace_seconds": 5, "poll_seconds": 0.05})
    o.hire(ROOT, "ceo", "Chief", "Run.")
    o.delegate(ROOT, "ceo", "T", "G", "A", budget=1)
    o.start_run_log("ceo")
    clock = Clock()
    waiting = Waiting(Scheduler(o, never_runner, echo=lambda _: None, clock=clock))
    waiting()
    clock.t += 5
    assert waiting().startswith("waiting on you:")


def test_serve_until_done_exits_when_budget_stalled_and_records_the_reason(org, stalled_on_budget):
    lines = []
    Scheduler(org, never_runner, echo=lines.append, clock=Clock(step=40)).serve(until_done=True)
    reason = 'waiting on you: "Rework the report" needs budget (ceo out of runs)'
    assert f"scheduler exiting: {reason}" in lines
    assert (org.root / EXIT_FILE).read_text().strip() == reason
    assert not (org.root / ".runtime" / "scheduler.pid").exists()
    assert describe_scheduler(org) == f"scheduler: stopped ({reason})"


def test_serve_until_done_exits_when_a_worker_keeps_failing(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    org.pause("ceo", "failures")
    lines = []
    Scheduler(org, never_runner, echo=lines.append, clock=Clock(step=40)).serve(until_done=True)
    assert any(x.startswith("scheduler exiting: waiting on you:") and "resume ceo" in x for x in lines)


def test_serve_without_until_done_keeps_going(org, stalled_on_budget):
    sched = Scheduler(org, never_runner, echo=lambda _: None, clock=Clock(step=40))
    waiting = Waiting(sched)
    sched.acquire()
    try:
        for _ in range(12):  # well past the grace period
            sched.tick()
            assert waiting() in ("", sched.waiting_on_user().text)
    finally:
        sched.release()
    assert not (org.root / EXIT_FILE).exists()


def test_a_plain_stall_waits_for_the_stall_ladder_before_the_exit(org):
    """No pause, no budget problem: ceo holds the task and does nothing. The reminders (stall_after) come first."""
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)  # read it, never reports
    clock = Clock()
    waiting = Waiting(Scheduler(org, never_runner, echo=lambda _: None, clock=clock))
    w = waiting_on_user(org)
    assert w.text == 'waiting on you: "Ship it" needs a decision (ceo holds it and nothing is running)' and not w.settled
    waiting()
    clock.t += 5000
    assert waiting() == ""  # not told root yet: the ladder may still wake ceo
    org.save_ledger("nudges", {task.id: {"step": 0, "at": clock.t}})  # reminded
    assert waiting() == ""
    org.save_ledger("nudges", {task.id: {"step": 1, "at": clock.t}})  # root told: nothing else will happen
    assert waiting_on_user(org).settled
    assert waiting().startswith('waiting on you: "Ship it" needs a decision')


@pytest.fixture
def root_server(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    return build_server(*resolve_binding())


def test_start_refuses_when_nothing_can_progress(org, stalled_on_budget, root_server, monkeypatch):
    monkeypatch.setattr("orgmcp.server.start_scheduler", lambda *a: pytest.fail("must not start"))
    for until_done in (True, False):
        out = call(root_server, "start", until_done=until_done)
        assert out.startswith("not started: nothing can progress without you")
        assert 'needs budget (ceo out of runs)' in out and 'send(to="ceo", body="<why>", budget=N)' in out
    org.send(ROOT, "ceo", "more", budget=2)
    seen = {}
    monkeypatch.setattr("orgmcp.server.start_scheduler", lambda o, m, u: seen.update(u=u) or 77)
    assert "scheduler started (pid 77" in call(root_server, "start") and seen == {"u": True}


def test_start_tool_description_mentions_the_waiting_exit(root_server):
    tools = {t.name: t.description for t in asyncio.run(root_server.list_tools())}
    assert "waiting for YOU" in tools["start"] and "start() refuses" in tools["start"]


# ----------------------------------------------------------------------- tool names in the prompts
def hire_writer(org, tmp_path, tools):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    org.hire(ROOT, "dev", "Developer", "Build.", tools=tools, workspace=str(ws))
    return ws


def test_orgmcp_write_and_read_say_they_are_organization_tools(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    monkeypatch.setenv("ORG_AGENT", "ceo")
    server = build_server(*resolve_binding())
    tools = {t.name: t.description for t in asyncio.run(server.list_tools())}
    assert "ORGANIZATION file" in tools["write"] and "@orgmcp/write" in tools["write"] and "NOT kiro's built-in `write`" in tools["write"]
    assert "ORGANIZATION's read tool" in tools["read"] and "@orgmcp/read" in tools["read"]
    assert call(server, "write", path="ceo/MEMORY.md", content="notes") == "wrote ceo/MEMORY.md (organization file)"
    assert org.memory("ceo") == "notes"


# ------------------------------------------------------------------------------ stray org files in a workspace
def script_runner(code: str):
    def build(org, addr, prompt):
        return [sys.executable, "-c", code], org.workspace_of(addr), dict(os.environ)

    return build


def run_to_end(sched, addr):
    sched.tick()
    deadline = time.time() + 20
    while sched.runs and time.time() < deadline:
        sched._reap()
        time.sleep(0.02)
    assert not sched.runs


STRAY = "import pathlib; p = pathlib.Path('dev/MEMORY.md'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('my notes')"


def test_stray_memory_in_the_workspace_is_logged_and_noticed_once(org, tmp_path):
    ws = hire_writer(org, tmp_path, ["write"])
    org.send(ROOT, "dev", "go", budget=5)
    lines = []
    sched = Scheduler(org, script_runner(STRAY), echo=lines.append)
    run_to_end(sched, "dev")
    assert (ws / "dev" / "MEMORY.md").is_file() and org.memory("dev") == ""  # nothing was moved
    log = next((org.root / "dev" / "runs").glob("*.log")).read_text()
    assert f"# warning: dev created org files in its workspace with the built-in `write`" in log and str(ws / "dev") in log
    assert any("dev: warning: org files in its workspace" in x for x in lines)
    assert org.ledger("strays")["dev"] == {"paths": [str(ws / "dev")], "told": False}

    prompt = org.run_prompt("dev", [])
    assert "# Notice from the runtime (shown once)" in prompt and str(ws / "dev") in prompt
    assert '`@orgmcp/org_write` (e.g. path="dev/MEMORY.md"' in prompt and "does not move or delete" in prompt
    assert "# Notice from the runtime" not in org.run_prompt("dev", [])  # once
    assert org.ledger("strays")["dev"]["told"] is True

    org.send(ROOT, "dev", "again", budget=0)
    (ws / "dev" / "MEMORY.md").write_text("more")  # a later stray is only logged, not announced again
    os.utime(ws / "dev" / "MEMORY.md", (time.time() + 5, time.time() + 5))
    run_to_end(sched, "dev")
    assert org.ledger("strays")["dev"]["told"] is True
    assert "# Notice from the runtime" not in org.run_prompt("dev", [])


def test_stray_nested_address_tree_is_detected(org, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    org.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["write"], workspace=str(ws))
    org.hire("lead", "an", "Analyst", "Analyse.", tools=["write"], workspace=str(ws))
    org.send(ROOT, "lead", "budget for the team", budget=5)
    org.send("lead", "lead/an", "go", budget=2)
    code = "import pathlib; p = pathlib.Path('lead/an/work/x.md'); p.parent.mkdir(parents=True); p.write_text('x')"
    sched = Scheduler(org, script_runner(code), echo=lambda _: None)
    sched._start("lead/an")
    deadline = time.time() + 20
    while sched.runs and time.time() < deadline:
        sched._reap()
        time.sleep(0.02)
    assert org.ledger("strays")["lead/an"]["paths"] == [str(ws / "lead" / "an")]


def test_no_warning_for_clean_runs_pre_existing_folders_or_agents_without_write(org, tmp_path):
    ws = hire_writer(org, tmp_path, ["write"])
    (ws / "dev").mkdir()  # already there before the run: not ours to flag
    org.send(ROOT, "dev", "go", budget=5)
    clean = "import pathlib; pathlib.Path('report.md').write_text('fine')"
    sched = Scheduler(org, script_runner(clean), echo=lambda _: None)
    run_to_end(sched, "dev")
    assert org.ledger("strays") == {}
    log = next((org.root / "dev" / "runs").glob("*.log")).read_text()
    assert "# warning:" not in log
    # an agent with a workspace but no built-in write cannot have written there: no probe at all
    org.hire(ROOT, "rd", "Reader", "Read.", tools=["read"], workspace=str(ws))
    assert org.runtime.stray_probe.probe("rd") == {}


class BrokenProbe(StrayProbe):
    """A probe of the workspace that cannot read it."""

    def probe(self, addr):
        raise OSError("boom")

    def found_since(self, before, after):
        return []


def test_a_failing_stray_probe_never_stops_a_run(org, tmp_path):
    hire_writer(org, tmp_path, ["write"])
    org.send(ROOT, "dev", "go", budget=5)
    lines = []
    org.runtime = dataclasses.replace(org.runtime, stray_probe=BrokenProbe())
    sched = Scheduler(org, script_runner("pass"), echo=lines.append)
    run_to_end(sched, "dev")
    assert any("stray check failed" in x for x in lines) and org.ledger("failures") == {}


def test_root_instructions_carry_the_finishing_rules_within_the_length_limit():
    for needle in ("settle its warnings (e.g. model policy) with the user", "or state them", "FIRST budget request",
                   "not after the reserve is gone", "declines", "unverified result (say the task stays open)",
                   "Final answer: as short as asked", "`stop` only if the user cancels"):
        assert needle in ROOT_INSTRUCTIONS, needle
    assert len(ROOT_INSTRUCTIONS) < 2800
