import asyncio
import os
import re
import sys
import time

import pytest
import testkit
import yaml
from testkit.e2e_world import build_server, resolve_binding
from testkit.scheduler_loop import loop_over

from orgmcp.core import ROOT, Org

EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"
TEAM = str(testkit.FAKE_TEAM_AGENT)


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def pid_of(server, text) -> str:
    """The plan_id propose_org returns for this blueprint text."""
    return re.search(r"^plan_id: (\w+)$", call(server, "propose_org", blueprint=text), re.M).group(1)


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


def run_team(org, mode_runner=None, limit=90.0):
    def runner(o, addr, prompt):
        return [sys.executable, TEAM], o.dir(addr), {**os.environ, "ORG_ROOT": str(o.root), "ORG_AGENT": addr}

    sched = loop_over(org, runner, echo=lambda _: None)
    sched.acquire()
    try:
        deadline = time.time() + limit
        while time.time() < deadline:
            if not sched.tick():
                return
            time.sleep(0.02)
        raise AssertionError("organization never went idle")
    finally:
        sched.release()


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

    out = call(server, "apply_org", blueprint=text, approved=True, plan_id=pid_of(server, text))  # 4. approved
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
    out = call(server, "apply_org", blueprint=text, approved=True, plan_id=pid_of(server, text))
    assert "created 4 agents" in out
    org = Org(target)
    for addr in ("lead/dev", "lead/qa", "lead/cr"):
        assert org.exists(addr)
    charter = (target / "lead" / "dev" / "AGENT.md").read_text()
    assert "- write" in charter and "- shell" in charter and f"workspace: {tmp_path / 'proj'}" in charter
    assert (tmp_path / "proj").is_dir()
