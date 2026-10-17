"""The "build me an org for <goal>" workflow through the root MCP tools, without kiro."""

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest
import yaml

from orgmcp import server as server_mod
from orgmcp.core import ROOT, Org
from orgmcp.scheduler import Scheduler
from orgmcp.server import ROOT_INSTRUCTIONS, build_server, resolve_binding

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "blueprint-research.yaml"
TEAM = str(Path(__file__).with_name("fake_team_agent.py"))


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    """A root server in setup mode (no organization yet) bound by ORG_ROOT, and the path."""
    target = tmp_path / "org"
    monkeypatch.setenv("ORG_ROOT", str(target))
    binding, me = resolve_binding()
    return build_server(binding, me), target


def research_text(tmp_path, **needs) -> str:
    bp = yaml.safe_load(EXAMPLE.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    bp["needs"].update(needs)
    return yaml.safe_dump(bp, sort_keys=False)


def code_text(tmp_path) -> str:
    ws = tmp_path / "proj"
    return yaml.safe_dump({
        "mission": "Build a small CLI that converts CSV to markdown tables.",
        "needs": {
            "scope": "csv2md CLI only; no web UI", "kind": "code",
            "deliverable": {"description": "A Python package csv2md with a CLI", "format": "python package"},
            "quality_bar": "tests pass from a clean checkout", "workspace": str(ws), "budget_runs": 40,
            "model_policy": "one model for all", "review": True, "approval": "approve plan first",
            "progress": "one line on request",
            "code": {"tests": "pytest, one per criterion", "packaging": "uv + pyproject", "commits": "local commits, never push"},
        },
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"},
            {"name": "cr", "template": "code-reviewer"}]}],
        "task": {"title": "Build csv2md", "goal": "Implement the csv2md CLI in the workspace",
                 "acceptance": ["`uv run pytest -q` passes with at least 5 tests",
                                "`csv2md in.csv` prints a markdown table to stdout"]},
    }, sort_keys=False)


def run_team(org, mode_runner=None, max_ticks=500):
    def runner(o, addr, prompt):
        return [sys.executable, TEAM], o.dir(addr), {**os.environ, "ORG_ROOT": str(o.root), "ORG_AGENT": addr}

    sched = Scheduler(org, runner, echo=lambda _: None)
    sched.acquire()
    try:
        for _ in range(max_ticks):
            if not sched.tick():
                return
            time.sleep(0.02)
        raise AssertionError("organization never went idle")
    finally:
        sched.release()


# --------------------------------------------------------------------------------------------- tools


def test_root_instructions_describe_the_workflow_and_keep_safety_lines(setup):
    server, target = setup
    text = server.instructions
    for needle in ("ONE orgmcp organization", "Never claim", "instead of substituting", "propose_org", "apply_org",
                   "approved=True", "start", "progress", "stop", "create_org", "EVERY acceptance criterion", str(target)):
        assert needle in text, needle
    assert len(ROOT_INSTRUCTIONS) < 2400  # sent on every connection: keep it short


def test_agents_get_none_of_the_goal_tools(tmp_path):
    org = Org.init(tmp_path / "o", "m")
    org.hire(ROOT, "ceo", "Chief", "Run it.", can_hire=True)
    names = {t.name for t in asyncio.run(build_server(org, "ceo").list_tools())}
    assert not names & {"propose_org", "apply_org", "progress", "create_org", "start", "stop"}


def test_propose_org_works_in_setup_mode_and_writes_nothing(setup, tmp_path):
    server, target = setup
    out = call(server, "propose_org", blueprint=research_text(tmp_path))
    assert "# Plan for approval" in out and "Reply 'approve'" in out
    assert f"Target organization: {target} (none yet" in out
    assert not target.exists() and not (tmp_path / "deliverables").exists()


def test_propose_org_reports_errors_in_the_plan(setup, tmp_path):
    server, _ = setup
    out = call(server, "propose_org", blueprint=research_text(tmp_path, review=True).replace("fact-checker", "researcher"))
    assert "Errors (" in out and "Cannot apply yet" in out


def test_propose_org_never_reads_files(setup, tmp_path):
    server, _ = setup
    secret = tmp_path / "secret.txt"
    secret.write_text("top: secret-value")
    msg = fails(server, "propose_org", blueprint=str(secret))
    assert "secret-value" not in msg and "mapping" in msg


def test_apply_org_refuses_without_approval(setup, tmp_path):
    server, target = setup
    call(server, "create_org", mission="m")
    msg = fails(server, "apply_org", blueprint=research_text(tmp_path))
    assert "user must approve" in msg and "propose_org" in msg
    assert Org(target).agents() == []


def test_apply_org_in_setup_mode_says_create_org_first(setup, tmp_path):
    server, target = setup
    msg = fails(server, "apply_org", blueprint=research_text(tmp_path), approved=True)
    assert "create_org" in msg and not target.exists()


def test_apply_org_with_errors_refuses_with_the_issues(setup, tmp_path):
    server, target = setup
    call(server, "create_org", mission="m")
    bad = research_text(tmp_path).replace("factcheck", "extra").replace("template: fact-checker", "template: researcher")
    msg = fails(server, "apply_org", blueprint=bad, approved=True)
    assert "nothing was created" in msg and "review" in msg
    assert Org(target).agents() == []


def test_progress_in_setup_mode_is_the_setup_state(setup):
    server, target = setup
    assert "create_org" in call(server, "progress")


def test_send_and_report_tool_texts_mention_returned_budget(tmp_path):
    org = Org.init(tmp_path / "o", "m")
    org.hire(ROOT, "ceo", "Chief", "Run it.", can_hire=True)
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    ceo = build_server(org, "ceo")
    org.begin_run("ceo")
    assert "returned 5 unspent run(s) of budget to root" in call(ceo, "report", task_id=task.id, status="done", summary="ok")
    sends = {t.name: t for t in asyncio.run(ceo.list_tools())}["send"].description
    assert "PARENT" in sends and "give some back earlier" in sends


def test_send_budget_to_parent_says_so(tmp_path):
    org = Org.init(tmp_path / "o", "m")
    org.hire(ROOT, "ceo", "Chief", "Run it.", can_hire=True)
    org.hire("ceo", "eng", "Eng", "Build.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.delegate("ceo", "ceo/eng", "T2", "g", "a", budget=3)
    eng = build_server(org, "ceo/eng")
    assert "with 2 run(s) of budget" in call(eng, "send", to="ceo", body="spare", budget=2)


# --------------------------------------------------------------------------------- end to end


def test_goal_to_delivery_end_to_end(setup, tmp_path):
    server, target = setup
    text = research_text(tmp_path)

    plan = call(server, "propose_org", blueprint=text)  # 1. plan, before anything exists
    assert "Reply 'approve'" in plan and not target.exists()
    assert "Errors (" not in plan

    assert "created the organization" in call(server, "create_org", mission="Competitor analysis")  # 2.
    assert "user must approve" in fails(server, "apply_org", blueprint=text)  # 3. refused without approval
    assert Org(target).agents() == []

    out = call(server, "apply_org", blueprint=text, approved=True)  # 4. approved
    assert "created 4 agents" in out and "call start()" in out
    org = Org(target)
    assert sorted(org.agents()) == ["lead", "lead/factcheck", "lead/researcher", "lead/writer"]
    assert "Research lead" in (target / "lead" / "AGENT.md").read_text()
    task = next(m for m in org.sent(ROOT) if m.type == "task")
    assert task.to == "lead" and "Covers exactly Obsidian" in task.body and task.budget >= 20

    first = call(server, "progress")  # before anything ran
    assert "Competitor analysis" in first and "runs 0 of" in first

    run_team(org)  # 5. the org works (fake agents)

    done = call(server, "progress", task_id=task.id)  # 6.
    assert ": done." in done and "lead/work/final.md" in done and "returned" in done
    result = next(m for m in org.received(ROOT) if m.type == "result")
    assert result.status == "done" and result.budget > 0
    assert sum(org.budget(a) for a in org.agents()) == 0  # everything unspent came back to root
    assert "returns" in call(server, "inbox")  # the result shows the returned runs
    assert "Needs you" not in call(server, "progress")


def test_code_goal_validates_and_applies(setup, tmp_path):
    server, target = setup
    text = code_text(tmp_path)
    plan = call(server, "propose_org", blueprint=text)
    assert "Errors (" not in plan and "Tests / packaging / commits" in plan
    call(server, "create_org", mission="csv2md")
    out = call(server, "apply_org", blueprint=text, approved=True)
    assert "created 4 agents" in out
    org = Org(target)
    for addr in ("lead/dev", "lead/qa", "lead/cr"):
        assert org.exists(addr)
    charter = (target / "lead" / "dev" / "AGENT.md").read_text()
    assert "- write" in charter and "- shell" in charter and f"workspace: {tmp_path / 'proj'}" in charter
    assert (tmp_path / "proj").is_dir()


# ------------------------------------------------------------------------------------ install-skill


def test_install_skill_to_a_temp_dest(tmp_path, capsys):
    from orgmcp.cli import main
    from orgmcp.skill import skill_source

    dest = tmp_path / "skills"
    main(["install-skill", "--dest", str(dest)])
    target = dest / "orgmcp" / "SKILL.md"
    out = capsys.readouterr().out
    assert str(target.resolve()) in out and target.read_text() == skill_source().read_text()
    main(["install-skill", "--dest", str(dest)])  # identical: fine, nothing changes
    assert "up to date" in capsys.readouterr().out


def test_install_skill_refuses_to_overwrite_a_different_file_without_force(tmp_path, capsys):
    from orgmcp.cli import main

    target = tmp_path / "skills" / "orgmcp" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("my own version\n")
    with pytest.raises(SystemExit):
        main(["install-skill", "--dest", str(tmp_path / "skills")])
    assert "--force" in capsys.readouterr().err and target.read_text() == "my own version\n"
    main(["install-skill", "--dest", str(tmp_path / "skills"), "--force"])
    assert target.read_text().startswith("---\nname: orgmcp")


def test_install_skill_defaults_to_home_kiro_skills(tmp_path, monkeypatch, capsys):
    from orgmcp.cli import main

    monkeypatch.setenv("HOME", str(tmp_path))
    main(["install-skill"])
    assert (tmp_path / ".kiro" / "skills" / "orgmcp" / "SKILL.md").is_file()
    assert str((tmp_path / ".kiro" / "skills" / "orgmcp" / "SKILL.md").resolve()) in capsys.readouterr().out


def test_skill_names_the_final_tools_and_signatures(tmp_path):
    from orgmcp.skill import skill_source

    text = skill_source().read_text()
    tools = {t.name for t in asyncio.run(build_server(Org.init(tmp_path / "o", "m"), ROOT).list_tools())}
    for name in ("create_org", "propose_org", "apply_org", "progress", "start", "stop", "whoami", "status", "inbox", "send"):
        assert name in tools and f"`{name}" in text, name
    assert "apply_org(blueprint=<the approved YAML, unchanged>, approved=True)" in text
    assert "create_org(mission=" in text and "propose_org(blueprint=" in text
