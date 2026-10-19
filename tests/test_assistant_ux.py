"""Assistant UX: the plan the user sees + plan_id, blueprint_example, waiting progress, scheduler until-done, skill rules."""

import asyncio
import os
import re
import sys
import time
from pathlib import Path

import pytest
import testkit
import yaml

from orgmcp import blueprint as bp_mod
from orgmcp import blueprint_examples
from orgmcp import scheduler as sched_mod
from orgmcp.app import wire_attention
from orgmcp.cli import main
from orgmcp.core import ROOT, Org, OrgError
from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.progress import WAIT_MAX, describe_progress, progress
from orgmcp.progress._reporter import DerivedProgressReporter
from orgmcp.progress.testing import FixedSnapshots, SpyProgressView
from orgmcp.scheduler import EXIT_FILE, Scheduler, describe_scheduler, nothing_to_do
from orgmcp.server import ROOT_INSTRUCTIONS, build_server, resolve_binding
from orgmcp.skill import skill_source

FAKE = str(testkit.FAKE_AGENT)
ALLOWED_WARNINGS = {"path-delivery", "path-parent", "workspace-new", "shell-unconfined"}  # shell-unconfined: the code example grants shell


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


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
def setup(tmp_path, monkeypatch):
    """A root server in setup mode (no organization yet) bound by ORG_ROOT."""
    target = tmp_path / "org"
    monkeypatch.setenv("ORG_ROOT", str(target))
    binding, me = resolve_binding()
    return build_server(binding, me), target


def example(server, kind="research") -> str:
    return call(server, "blueprint_example", kind=kind)


def plan_id_in(text: str) -> str:
    return re.search(r"^plan_id: (\w+)$", text, re.M).group(1)


def block(text: str) -> str:
    return text[text.index(bp_mod.PLAN_HEADING):text.index(bp_mod.PLAN_END)].rstrip()


# ----------------------------------------------------------------------------------- plan for you


def test_propose_org_returns_the_block_then_details_then_plan_id(setup):
    server, target = setup
    out = call(server, "propose_org", blueprint=example(server, "documents"))
    assert out.index("Target organization") < out.index(bp_mod.PLAN_HEADING) < out.index(bp_mod.PLAN_END) \
        < out.index("Details") < out.index("# Plan for approval") < out.index("plan_id: ")
    assert not target.exists()  # still writes nothing


def test_the_plan_block_is_compact_and_has_everything_the_user_approves(setup, env):
    server, _ = setup
    b = block(call(server, "propose_org", blueprint=example(server, "documents")))
    assert len(b.splitlines()) <= 42
    for needle in ("Goal:", "What I understood you need", "Team (4 agents)", "lead (Manager, model claude-sonnet-5.5)",
                   "Models: claude-sonnet-5.5 for every agent", "reader", "can read files", "cannot change your files", "Budget: 19 runs planned",
                   "your cap is 25", "lead starts with 19", "Checking: reviewer", "Deliverable:", "Delivered to:",
                   str(env / "deliverables"), "(I copy it there after checking it)", "Done when ALL of these hold",
                   "1. Covers", "Checkpoints:", "Your files (read-only)", "approve"):
        assert needle in b, needle


def test_block_shows_a_code_workspace_and_write_access(setup, env):
    server, _ = setup
    b = block(call(server, "propose_org", blueprint=example(server, "code")))
    assert f"changes files only in {env / '<project-folder>'}" in b and "run commands" in b
    assert "Tests / packaging / commits" in b and len(b.splitlines()) <= 42
    assert f"Delivered to: the workspace {env / '<project-folder>'}" in b


def test_a_plan_with_errors_is_a_draft_without_plan_id(setup):
    server, _ = setup
    text = example(server).replace("template: fact-checker", "template: researcher")
    out = call(server, "propose_org", blueprint=text)
    assert bp_mod.PLAN_DRAFT_HEADING in out and bp_mod.PLAN_HEADING not in out
    assert "Errors (" in out and re.search(r"^plan_id: none", out, re.M)
    assert "do not show this to the user" in out


def test_plan_id_is_stable_and_changes_with_the_blueprint(setup):
    server, _ = setup
    text = example(server)
    first = plan_id_in(call(server, "propose_org", blueprint=text))
    assert first == plan_id_in(call(server, "propose_org", blueprint=text))
    assert re.fullmatch(r"[0-9a-f]{12}", first)
    bp = bp_mod.load_text(text)
    assert bp_mod.plan_id(bp) == first
    # formatting, comments and key order do not matter; any value does
    reordered = yaml.safe_dump(bp, sort_keys=True)
    assert bp_mod.plan_id(bp_mod.load_text(reordered)) == first
    changed = text.replace("max_words: 1500", "max_words: 1501")
    assert plan_id_in(call(server, "propose_org", blueprint=changed)) != first


def test_plan_id_does_not_depend_on_the_organization(setup):
    server, _ = setup
    text = example(server)
    before = plan_id_in(call(server, "propose_org", blueprint=text))
    call(server, "create_org", mission="m")
    assert plan_id_in(call(server, "propose_org", blueprint=text)) == before


# --------------------------------------------------------------------------------------- apply_org


def test_apply_org_needs_approval_and_the_plan_id_of_this_blueprint(setup):
    server, target = setup
    call(server, "create_org", mission="m")
    text = example(server)
    pid = plan_id_in(call(server, "propose_org", blueprint=text))

    msg = fails(server, "apply_org", blueprint=text, plan_id=pid)  # plan_id but no approval
    assert "user must approve" in msg and "PLAN FOR YOU" in msg
    msg = fails(server, "apply_org", blueprint=text, approved=True)  # approval but no plan_id
    assert "plan_id is missing" in msg and "propose_org" in msg and "PLAN FOR YOU" in msg
    msg = fails(server, "apply_org", blueprint=text, approved=True, plan_id="000000000000")  # a different plan
    assert "does not match" in msg and pid not in msg  # the right id is not leaked
    other = text.replace("max_words: 1500", "max_words: 1400").replace("At most 1500 words", "At most 1400 words")
    msg = fails(server, "apply_org", blueprint=other, approved=True, plan_id=pid)  # approved one, applying another
    assert "does not match" in msg
    assert Org(target).agents() == []

    out = call(server, "apply_org", blueprint=text, approved=True, plan_id=pid)
    assert "created 4 agents" in out and "start()" in out
    assert sorted(Org(target).agents()) == ["lead", "lead/factcheck", "lead/researcher", "lead/writer"]


def test_apply_org_plan_id_survives_a_new_server(setup, tmp_path, monkeypatch):
    server, target = setup
    call(server, "create_org", mission="m")
    text = example(server)
    pid = plan_id_in(call(server, "propose_org", blueprint=text))
    monkeypatch.setenv("ORG_ROOT", str(target))
    restarted = build_server(*resolve_binding())  # stateless: a restart between propose and apply is fine
    assert "created 4 agents" in call(restarted, "apply_org", blueprint=text, approved=True, plan_id=pid)


def test_apply_org_with_the_plan_id_still_refuses_a_blueprint_with_errors(setup):
    server, target = setup
    call(server, "create_org", mission="m")
    bad = example(server).replace("template: fact-checker", "template: researcher")
    pid = bp_mod.plan_id(bp_mod.load_text(bad))
    msg = fails(server, "apply_org", blueprint=bad, approved=True, plan_id=pid)
    assert "nothing was created" in msg and Org(target).agents() == []


# ----------------------------------------------------------------------------------- blueprint_example


@pytest.mark.parametrize("kind", blueprint_examples.KINDS)
def test_every_example_validates_and_round_trips_through_propose_org(setup, kind):
    server, _ = setup
    text = example(server, kind)
    issues = bp_mod.validate(bp_mod.load_text(text))
    assert not bp_mod.errors(issues), [i.render() for i in issues]
    assert {i.code for i in issues} <= ALLOWED_WARNINGS, [i.render() for i in issues]
    out = call(server, "propose_org", blueprint=text)  # the whole returned text is valid YAML with a comment header
    assert bp_mod.PLAN_HEADING in out and plan_id_in(out)
    assert text.lstrip().startswith("# Blueprint schema in one paragraph")


def test_example_kinds_differ_in_what_they_need(setup):
    server, _ = setup
    research, docs, code = (bp_mod.load_text(example(server, k)) for k in ("research", "documents", "code"))
    assert any("web_search" in a.tools for a in bp_mod._resolve(research, None, [Path("/")], []))  # a web researcher
    assert "inputs" in docs["needs"] and "no web" in docs["needs"]["sources"].lower()
    assert code["needs"]["workspace"] and code["needs"]["kind"] == "code" and "commits" in code["needs"]["code"]
    assert "inputs" not in research["needs"]


def test_example_paths_start_in_the_users_current_directory(setup, env):
    server, _ = setup
    for kind in ("research", "documents"):
        assert str(env / "deliverables") in example(server, kind)
    assert str(env / "<project-folder>") in example(server, "code")


def test_unknown_example_kind_lists_the_kinds(setup):
    server, _ = setup
    msg = fails(server, "blueprint_example", kind="poetry")
    for k in blueprint_examples.KINDS:
        assert k in msg


def test_example_works_in_setup_mode_and_is_the_default_research(setup):
    server, target = setup
    assert call(server, "blueprint_example") == example(server, "research") and not target.exists()


def test_tool_descriptions_and_instructions_point_at_no_repo_files(setup):
    server, _ = setup
    tools = {t.name: t.description for t in asyncio.run(server.list_tools())}
    texts = [server.instructions, *tools.values()]
    for t in texts:
        assert "examples/" not in t and "SKILL.md" not in t and ".yaml" not in t
    desc = tools["propose_org"]
    assert "blueprint_example(kind)" in desc and "PLAN FOR YOU" in desc and "plan_id" in desc
    for key in ("mission", "needs", "agents", "task", "acceptance", "budget_runs", "inputs", "workspace", "template"):
        assert key in desc, key  # a compact schema: self-sufficient without the skill
    assert "plan_id" in tools["apply_org"] and "wait_seconds" in tools["progress"] and "until_done" in tools["start"]


# ------------------------------------------------------------------------------ skill and instructions


def test_skill_and_instructions_carry_the_new_rules(setup):
    server, _ = setup
    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125
    for needle in ("PLAN FOR YOU", "exactly as written", "plan_id=<from propose_org>", "blueprint_example(kind)",
                   "Never invent a default", "deliverables/", "Never say \"I'll tell you when it's done\"",
                   "progress(wait_seconds=", "ask \"status?\"", "ends by itself", "`stop()` only if the user cancels"):
        assert needle in skill, needle
    text = server.instructions
    for needle in ("PLAN FOR YOU", "plan_id=<from propose_org>", "blueprint_example(kind)", "never invent", "`deliverables/`",
                   "Never promise to tell the user later", "progress(wait_seconds=N)", "\"status?\"", "`stop` only if the user cancels"):
        assert needle in text, needle
    assert len(ROOT_INSTRUCTIONS) < 2800


# -------------------------------------------------------------------------------------- progress wait


class Clock:
    """A fake clock whose ``sleep`` advances time and can run an action at the n-th sleep."""

    def __init__(self, actions=None):
        self.now, self.sleeps, self.actions = 0.0, 0, actions or {}

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps += 1
        self.now += seconds
        action = self.actions.get(self.sleeps)
        if action:
            action()


def waiting(org, clock, wait=60, poll=2.0, task_id=None):
    return progress(org, task_id, wait_seconds=wait, poll=poll, sleep=clock.sleep, clock=clock)


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


def test_wait_returns_when_a_task_finishes(org, task):
    def finish():
        org.begin_run("ceo")
        org.report("ceo", task.id, "done", "Finished.")
        org.end_run("ceo", ok=True)

    clock = Clock({3: finish})
    out = waiting(org, clock)
    first, *rest = out.splitlines()
    assert first == 'Changed after waiting 6s: "Write the report": working -> done'
    assert any(': done.' in line for line in rest) and clock.sleeps == 3


def test_wait_returns_when_a_task_is_blocked_and_says_why(org, task):
    def block_it():
        org.begin_run("ceo")
        org.report("ceo", task.id, "blocked", "Need the API key.")
        org.end_run("ceo", ok=True)

    out = waiting(org, Clock({1: block_it}))
    assert out.splitlines()[0].startswith('Changed after waiting 2s: "Write the report": working -> blocked: Need the API key')


def test_wait_returns_when_something_new_needs_the_human(org, task):
    org.begin_run("ceo")
    clock = Clock({2: lambda: org.send("ceo", ROOT, "May I spend 5 more runs?", title="Budget question")})
    out = waiting(org, clock)
    assert out.startswith("Changed after waiting 4s: new item for you: Needs you: note from ceo")
    assert "Budget question" in out.splitlines()[0]


def test_an_item_that_was_already_waiting_does_not_end_the_wait(org, task):
    org.begin_run("ceo")
    org.send("ceo", ROOT, "Old question", title="Old")
    out = waiting(org, Clock(), wait=10, poll=5)
    assert out.startswith("Waited 10s:") and "Old" in out  # still listed, but not a change


def test_wait_times_out_with_the_current_lines(org, task):
    clock = Clock()
    out = waiting(org, clock, wait=10, poll=3)
    assert out.startswith("Waited 10s: no task finished") and "progress(wait_seconds=" in out
    assert '"Write the report": working' in out
    assert clock.now == 10 and clock.sleeps == 4  # 3 + 3 + 3 + 1: never past the deadline


def test_wait_is_capped_at_900_seconds(org, task):
    clock = Clock()
    out = waiting(org, clock, wait=10**6, poll=300)
    assert out.startswith("Waited 15m") and clock.now == WAIT_MAX == 900 and clock.sleeps == 3


def test_wait_zero_or_negative_does_not_wait(org, task):
    for w in (0, -5):
        clock = Clock()
        assert waiting(org, clock, wait=w) == progress(org) and clock.sleeps == 0


def test_nothing_to_wait_for_when_every_task_is_finished(org, task):
    org.begin_run("ceo")
    org.report("ceo", task.id, "done", "Finished.")
    clock = Clock()
    out = waiting(org, clock)
    assert out.startswith("Nothing to wait for") and ": done." in out and clock.sleeps == 0


def test_a_stall_must_persist_for_two_looks_before_it_ends_the_wait(org, task):
    def reads_and_stops():  # ceo reads its task, then nothing happens: stalled
        org.begin_run("ceo")
        org.end_run("ceo", ok=True)

    clock = Clock({1: reads_and_stops})
    out = waiting(org, clock)
    assert out.splitlines()[0].startswith('Changed after waiting 4s: "Write the report": working -> stalled') and clock.sleeps == 2


def test_a_hand_over_that_looks_like_a_stall_once_is_ignored(org, task):
    def reads():
        org.begin_run("ceo")
        org.end_run("ceo", ok=True)

    clock = Clock({1: reads, 2: lambda: org.delegate("ceo", "ceo/eng", "Sub", "goal", "criteria", budget=3)})
    out = waiting(org, clock, wait=8)
    assert out.startswith("Waited 8s:")


def test_waiting_only_reads_files(org, task):
    def snapshot():
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in org.root.rglob("*") if p.is_file())

    before = snapshot()
    waiting(org, Clock(), wait=20, poll=2)
    assert snapshot() == before


def test_wait_for_one_task_ignores_the_others(org, task):
    other = org.delegate(ROOT, "ceo", "Other", "goal", "criteria", budget=2)

    def finish_other():
        org.begin_run("ceo")
        org.report("ceo", other.id, "done", "x")

    out = waiting(org, Clock({1: finish_other}), wait=6, poll=2, task_id=task.id)
    assert out.startswith("Waited 6s:")


def test_describe_progress_adds_the_scheduler_line_and_does_not_wait_without_one(org, task):
    t0 = time.monotonic()
    out = describe_progress(org, None, 600)  # no scheduler is running: it must answer at once
    assert time.monotonic() - t0 < 5
    assert out.startswith("Not waiting: no scheduler is running") and "working" in out
    assert out.splitlines()[-1].startswith("scheduler: stopped - open tasks do not move until it is started")


def test_describe_progress_waits_when_a_scheduler_runs(org, task):
    scheduler = FakeSchedulerStatus(SchedulerState("running", 1, "x"))
    view = SpyProgressView("lines")
    reporter = DerivedProgressReporter(view, FixedSnapshots(), scheduler, wire_attention.waiting_on_user_of(org.runtime), org.runtime.task_query)
    assert reporter.describe_progress(None, 30) == "lines\nscheduler: running (pid 1, since x)"
    assert view.kwargs == {"wait_seconds": 30}


def test_progress_tool_and_cli_take_the_wait(org, task, capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(*resolve_binding())
    tool = next(t for t in asyncio.run(server.list_tools()) if t.name == "progress")
    assert set(tool.inputSchema["properties"]) == {"task_id", "wait_seconds"}
    out = call(server, "progress", wait_seconds=300)  # stopped scheduler: answers at once
    assert out.startswith("Not waiting") and f"(task {task.id})" in out
    main(["--root", str(org.root), "progress", task.id, "--wait", "300"])
    cli = capsys.readouterr().out
    assert cli.startswith("Not waiting") and "scheduler: stopped" in cli


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


def test_status_and_progress_show_the_finished_scheduler_until_new_work_arrives(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    Scheduler(org, fake_runner("work"), echo=lambda _: None).serve(until_done=True)
    assert describe_progress(org).splitlines()[-1] == "scheduler: stopped (finished: no open tasks)"
    server = build_server(org, ROOT)
    assert "scheduler: stopped (finished: no open tasks)" in call(server, "status")
    org.delegate(ROOT, "ceo", "More", "g", "a", budget=3)  # new work: the old reason no longer holds
    assert describe_scheduler(org) == "scheduler: stopped"
    assert describe_progress(org).splitlines()[-1].startswith("scheduler: stopped - open tasks do not move")


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


def test_cli_run_until_done_exits_and_logs_the_reason(org, capsys):
    main(["--root", str(org.root), "run", "--until-done"])  # nothing to do: returns at once
    assert "scheduler exiting: finished: no open tasks" in capsys.readouterr().out
    assert describe_scheduler(org) == "scheduler: stopped (finished: no open tasks)"
    with pytest.raises(SystemExit):
        main(["--root", str(org.root), "run", "--until-done", "--once"])


def test_cli_status_shows_the_scheduler(org, capsys):
    main(["--root", str(org.root), "run", "--until-done"])
    capsys.readouterr()
    main(["--root", str(org.root), "status"])
    assert "scheduler: stopped (finished: no open tasks)" in capsys.readouterr().out


def test_scheduler_command_adds_the_flag_only_when_asked(org):
    assert "--until-done" not in sched_mod.scheduler_command(org.root, 3)
    assert sched_mod.scheduler_command(org.root, 3, True)[-1] == "--until-done"


def test_start_tool_defaults_to_until_done(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(*resolve_binding())
    out = call(server, "start")  # empty org: nothing to run, so nothing is started
    assert out.startswith("not started: there is nothing to run") and not (org.root / ".runtime" / "scheduler.pid").exists()


def test_start_tool_passes_until_done_to_the_scheduler(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    server = build_server(*resolve_binding())
    seen = {}
    monkeypatch.setattr("orgmcp.server.start_scheduler", lambda o, m, u: seen.update(max=m, until_done=u) or 4242)
    assert "exits by itself when the work is done" in call(server, "start", max_runs=2)
    assert seen == {"max": 2, "until_done": True}
    assert "runs until stop()" in call(server, "start", until_done=False)
    assert seen["until_done"] is False


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
