"""Finishing and naming: until-done exit when the user must act, the plan's failure policy and sentence-safe lines,
orgmcp vs built-in tool names in the prompts, stray org files in a workspace, and the skill/instruction rules."""

import asyncio
import dataclasses
import os
import re
import sys
import time
from pathlib import Path

import pytest

from orgmcp import blueprint as bp_mod
from orgmcp import blueprint_examples
from orgmcp import scheduler as sched_mod
from orgmcp import templates
from orgmcp.app import wire_attention
from orgmcp.core import ROOT, Org
from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.progress import describe_progress
from orgmcp.progress.testing import FixedLegacyParts
from orgmcp.scheduler import EXIT_FILE, Scheduler, describe_scheduler, waiting_on_user
from orgmcp.server import ROOT_INSTRUCTIONS, build_server, resolve_binding
from orgmcp.skill import skill_source
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


def quiet(org, **kw):
    return Scheduler(org, never_runner, echo=lambda _: None, **kw)


# ------------------------------------------------------------------------------- until-done: waiting on the user


@pytest.fixture
def stalled_on_budget(org):
    """root's only task sits with ceo, which has used its single run: the task is unread and cannot be served."""
    task = org.delegate(ROOT, "ceo", "Rework the report", "Fix it", "It is fixed", budget=1)
    org.start_run_log("ceo")  # the one run is gone
    assert org.budget("ceo") == 0 and org.unread("ceo") == 1
    return task


def test_budget_stalled_task_is_waiting_on_the_user(org, stalled_on_budget):
    w = waiting_on_user(org)
    assert w.text == 'waiting on you: "Rework the report" needs budget (ceo out of runs)' and w.settled
    assert 'send(to="ceo", body="<why>", budget=N)' in w.options and "call start()" in w.options
    assert "accept what exists so far" in w.options and "stop()" in w.options


def test_paused_for_failures_asks_for_a_human_resume(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    org.pause("ceo", "failures")
    w = waiting_on_user(org)
    assert w.text == 'waiting on you: "Ship it" needs you to resume ceo (it keeps failing)'
    assert "`orgmcp resume ceo`" in w.options


def test_a_paused_worker_deep_in_the_subtree_counts_and_budget_goes_to_the_assignee(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=6)
    org.begin_run("ceo")
    org.delegate("ceo", "ceo/eng", "Build", "Build", "Built", budget=1)
    org.end_run("ceo", ok=True)
    org.start_run_log("ceo/eng")  # eng used its only run, has the unread task
    org.pause("ceo/eng", "budget")
    w = waiting_on_user(org)
    assert "needs budget (ceo/eng out of runs)" in w.text and 'send(to="ceo"' in w.options


def test_nothing_is_waiting_while_something_can_run_or_runs(org):
    assert waiting_on_user(org) is None  # no open task
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    assert waiting_on_user(org) is None  # ceo can run
    assert waiting_on_user(org, running={"ceo"}) is None  # or is running
    org.begin_run("ceo")
    assert waiting_on_user(org) is None  # inflight counts as running
    org.end_run("ceo", ok=True)
    assert waiting_on_user(org, blocked={"ceo"}) is None  # an orphaned run may still be alive


def test_a_grant_makes_the_task_runnable_again(org, stalled_on_budget):
    assert waiting_on_user(org)
    org.send(ROOT, "ceo", "more runs please", budget=2)
    assert waiting_on_user(org) is None


def test_the_run_cap_counts_as_waiting(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    w = waiting_on_user(org, can_start=False)
    assert "the run cap (max_runs) was reached" in w.text and "higher max_runs" in w.options


def test_grace_period_with_a_fake_clock(org, stalled_on_budget):
    clock, lines = Clock(), []
    sched = Scheduler(org, never_runner, echo=lines.append, clock=clock)
    assert sched._check_waiting() == ""  # first sight: the count starts
    assert any("Exiting in 300s unless something changes" in x for x in lines)
    clock.t += 299
    assert sched._check_waiting() == ""
    clock.t += 1
    assert sched._check_waiting() == 'waiting on you: "Rework the report" needs budget (ceo out of runs)'


def test_a_change_restarts_the_grace_period(org, stalled_on_budget):
    clock = Clock()
    sched = Scheduler(org, never_runner, echo=lambda _: None, clock=clock)
    sched._check_waiting()
    clock.t += 250
    org.send(ROOT, "ceo", "more", budget=1)  # the user acts: runnable
    assert sched._check_waiting() == "" and sched._waiting_since is None
    org.start_run_log("ceo")  # ...and it is stuck again
    clock.t += 100
    assert sched._check_waiting() == "" and sched._waiting_since is not None
    clock.t += 299
    assert sched._check_waiting() == ""
    clock.t += 2
    assert sched._check_waiting().startswith("waiting on you:")


def test_the_grace_is_configurable(tmp_path):
    o = Org.init(tmp_path / "o", "m", {"until_done_grace_seconds": 5, "poll_seconds": 0.05})
    o.hire(ROOT, "ceo", "Chief", "Run.")
    o.delegate(ROOT, "ceo", "T", "G", "A", budget=1)
    o.start_run_log("ceo")
    clock = Clock()
    sched = Scheduler(o, never_runner, echo=lambda _: None, clock=clock)
    sched._check_waiting()
    clock.t += 5
    assert sched._check_waiting().startswith("waiting on you:")


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
    sched.acquire()
    try:
        for _ in range(12):  # well past the grace period
            sched.tick()
            assert sched._check_waiting() in ("", sched.waiting_on_user().text)
    finally:
        sched.release()
    assert not (org.root / EXIT_FILE).exists()


def test_a_plain_stall_waits_for_the_stall_ladder_before_the_exit(org):
    """No pause, no budget problem: ceo holds the task and does nothing. The reminders (stall_after) come first."""
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)  # read it, never reports
    clock = Clock()
    sched = Scheduler(org, never_runner, echo=lambda _: None, clock=clock)
    w = waiting_on_user(org)
    assert w.text == 'waiting on you: "Ship it" needs a decision (ceo holds it and nothing is running)' and not w.settled
    sched._check_waiting()
    clock.t += 5000
    assert sched._check_waiting() == ""  # not told root yet: the ladder may still wake ceo
    org.save_ledger("nudges", {task.id: {"step": 0, "at": clock.t}})  # reminded
    assert sched._check_waiting() == ""
    org.save_ledger("nudges", {task.id: {"step": 1, "at": clock.t}})  # root told: nothing else will happen
    assert waiting_on_user(org).settled
    assert sched._check_waiting().startswith('waiting on you: "Ship it" needs a decision')


def test_progress_shows_the_reason_and_the_options_and_does_not_wait(org, stalled_on_budget):
    out = describe_progress(org, None, 300)
    assert out.startswith("Not waiting: nothing can progress without you. ")
    last = out.splitlines()[-1]
    assert last.startswith('scheduler: stopped (waiting on you: "Rework the report" needs budget (ceo out of runs)) - ')
    assert "nothing moves until you act" in last and 'send(to="ceo"' in last and "accept what exists so far" in last


def test_progress_while_the_scheduler_runs_still_says_so(org, stalled_on_budget, monkeypatch):
    rt = org.runtime
    running = FixedLegacyParts(
        rt.human_queue, rt.case_history, rt.service_reports, FakeSchedulerStatus(SchedulerState("running", 1, "x")), wire_attention.waiting_on_user_of(rt),
    )
    monkeypatch.setattr(org, "runtime", dataclasses.replace(rt, progress_parts=running))
    out = describe_progress(org)
    assert 'waiting on you: "Rework the report" needs budget' in out and "exits by itself soon" in out


def test_status_line_of_an_org_that_can_progress_is_unchanged(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    assert describe_scheduler(org) == "scheduler: stopped"
    assert describe_progress(org).splitlines()[-1].startswith("scheduler: stopped - open tasks do not move")


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


# --------------------------------------------------------------------------------------------- the plan block


def doc_bp(tmp_path, monkeypatch):
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))
    (tmp_path / "<folder-with-your-files>").mkdir(exist_ok=True)
    return bp_mod.load_text(blueprint_examples.example("documents", tmp_path))


def goal_line(block: str) -> str:
    return next(x for x in block.splitlines() if x.startswith("Goal: "))


def test_failure_policy_line_under_the_budget(tmp_path, monkeypatch):
    block = bp_mod.plan_for_user(doc_bp(tmp_path, monkeypatch))
    lines = block.splitlines()
    i = next(n for n, x in enumerate(lines) if x.startswith("Budget:"))
    policy = next(x for x in lines[i:i + 4] if x.startswith("If the check still fails after one rework"))
    total, minimum = map(int, re.search(r"Budget: (\d+) runs planned.*minimum for one review and rework is (\d+)", lines[i]).groups())
    reserve = total - minimum
    assert reserve > 0
    assert policy == (f"If the check still fails after one rework, I'll come back to you with options before spending the "
                      f"reserve (about {reserve} runs); nothing beyond the {total} planned runs is spent without your OK.")
    assert len(lines) <= 42


def test_failure_policy_without_a_reserve(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    minimum = int(re.search(r"minimum for one review and rework is (\d+)", bp_mod.plan_for_user(bp)).group(1))
    bp["task"]["budget"] = minimum
    block = bp_mod.plan_for_user(bp)
    assert (f"If the check still fails after one rework, I'll come back to you with options; the plan has no reserve "
            f"beyond that rework, and nothing beyond the {minimum} planned runs is spent without your OK.") in block


def test_a_long_mission_is_shown_whole_in_the_goal_line(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    mission = ("Research the competitive landscape of the three products and summarise pricing, positioning and recent "
               "releases for a leadership audience, citing a source for every claim. Highlight the top three risks "
               "for the next quarter and say how sure we are about each of them. " * 2).strip()
    assert 220 < len(mission) < 800
    bp["mission"] = mission
    assert goal_line(bp_mod.plan_for_user(bp)) == f"Goal: {mission}"


def test_a_very_long_mission_is_cut_at_a_sentence_boundary(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    sentences = [f"Sentence number {i} says something rather long about the work to do, " + "x" * 280 + "." for i in range(1, 5)]
    bp["mission"] = " ".join(sentences)
    goal = goal_line(bp_mod.plan_for_user(bp))
    assert goal == f"Goal: {sentences[0]} {sentences[1]} (the rest is in the details)"
    assert "..." not in goal and "…" not in goal


def test_a_single_long_sentence_is_never_cut(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    one = "Do the whole thing " + "and then some more " * 80 + "properly."
    bp["mission"] = one
    assert goal_line(bp_mod.plan_for_user(bp)) == f"Goal: {one}"


def test_clip_helper_and_other_lines_do_not_cut_mid_sentence(tmp_path, monkeypatch):
    assert bp_mod._clip("Short.") == "Short."
    text = "First one. " + "Second sentence here. " * 30 + "Last."
    out = bp_mod._clip(text, 100)
    assert out.endswith(" (the rest is in the details)") and out.removesuffix(" (the rest is in the details)").endswith(".")
    bp = doc_bp(tmp_path, monkeypatch)
    long_criterion = "The report lists every competitor by name, with a price for each plan, and says where the price was found " * 4 + "end."
    bp["task"]["acceptance"] = [long_criterion, "Second criterion."]
    bp["needs"]["scope"] = "Scope part one is short. " + "More scope detail that goes on and on. " * 20
    block = bp_mod.plan_for_user(bp)
    assert f"  1. {long_criterion}" in block  # the contract is shown in full
    scope = next(x for x in block.splitlines() if x.startswith("- Scope: "))
    assert scope.endswith(" (the rest is in the details)") and "..." not in scope


# ----------------------------------------------------------------------- tool names in the prompts


def hire_writer(org, tmp_path, tools):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    org.hire(ROOT, "dev", "Developer", "Build.", tools=tools, workspace=str(ws))
    return ws


def test_prompt_of_an_agent_with_built_ins_separates_the_two_kinds_of_tools(org, tmp_path):
    hire_writer(org, tmp_path, ["read", "write", "shell"])
    text = org.run_prompt("dev", [])
    files = text.split("- Files:")[1].split("# New messages")[0]
    # the built-ins `read`/`write` hide orgmcp's tools of the same name (studies/F-read-experiment, F2-tool-names):
    # this agent has them as `org_read` / `org_write`
    assert "orgmcp tools (shown as `@orgmcp/org_write`, `@orgmcp/org_read`, ...)" in files
    assert "kiro's built-in `read`, `shell`, `write`" in files and "they write and run only in the workspace and never change the org" in files
    assert "`dev/MEMORY.md`, `dev/work/`" in files
    assert "written with `@orgmcp/org_write`, never with the built-in `write`" in files
    assert "the orgmcp write tool is `@orgmcp/org_write` for you: use it for MEMORY.md and org files" in files
    assert "Your `read` is kiro's built-in: it reads org files too" in files and "`@orgmcp/org_read` for you" in files
    assert f"ABSOLUTE path, `{org.root}/<path in the org>`" in files
    assert '`@orgmcp/org_write`(path="dev/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`)' in text


def test_agent_with_only_a_built_in_read_and_no_workspace_gets_the_naming_text(org):
    org.hire(ROOT, "rd", "Reader", "Read.", tools=["read"])
    files = org.run_prompt("rd", []).split("- Files:")[1]
    assert "kiro's built-in `read`" in files and "`@orgmcp/org_read`" in files


def test_agent_without_built_ins_has_no_files_section_but_the_orgmcp_memory_line(org):
    text = org.run_prompt("ceo", [])
    assert "- Files:" not in text and "never with the built-in" not in text
    assert '`@orgmcp/write`(path="ceo/MEMORY.md", ...)' in text


def test_org_rules_name_the_orgmcp_tools_unambiguously(tmp_path):
    rules = Org.init(tmp_path / "o", "m").rules()
    assert rules == templates.org_rules("m").strip()
    assert "kiro shows them as `@orgmcp/<tool>`, e.g. `@orgmcp/write`" in rules
    assert "built-in `write`/`read`/`shell`, those are different tools that reach the workspace only, never the org" in rules
    assert "with `@orgmcp/write`: artifacts go in `<you>/work/`" in rules and "with `@orgmcp/read`" in rules
    assert "(with `@orgmcp/write`, never the built-in `write`)" in rules


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


# --------------------------------------------------------------------------------- skill and instructions


def test_skill_carries_the_finishing_rules():
    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125
    for needle in ("settle them with the user BEFORE you", "ask for approval", "state each one plainly",
                   "what happens if the check still fails after one rework",
                   "Ask at the FIRST budget request", "never wait until the reserve", "waiting on you",
                   "`start()` refuses until something changes", "declines more budget",
                   "unverified or partial result (say the task\n   stays open/blocked, not done)",
                   "shorter still when the user asks for a short answer", "one line per criterion",
                   "`stop()` only if the user cancels"):
        assert needle in skill, needle


def test_root_instructions_carry_the_finishing_rules_within_the_length_limit():
    for needle in ("settle its warnings (e.g. model policy) with the user", "or state them", "FIRST budget request",
                   "not after the reserve is gone", "declines", "unverified result (say the task stays open)",
                   "Final answer: as short as asked", "`stop` only if the user cancels"):
        assert needle in ROOT_INSTRUCTIONS, needle
    assert len(ROOT_INSTRUCTIONS) < 2800
