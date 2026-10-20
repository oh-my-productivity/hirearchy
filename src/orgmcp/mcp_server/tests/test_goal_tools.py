# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio
import re

import pytest
import testkit
import testkit.legacy.yaml as yaml
from testkit.legacy.orgmcp.core import ROOT, Org
from testkit.legacy.orgmcp.server import ROOT_INSTRUCTIONS, build_server, resolve_binding

from orgmcp import blueprint as blueprint_mod

EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"


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


# --------------------------------------------------------------------------------------------- tools
def test_root_instructions_describe_the_workflow_and_keep_safety_lines(setup):
    server, target = setup
    text = server.instructions
    for needle in ("ONE orgmcp organization", "Never claim", "instead of substituting", "propose_org", "apply_org",
                   "approved=True", "start", "progress", "stop", "create_org", "EVERY acceptance criterion", str(target)):
        assert needle in text, needle
    assert len(ROOT_INSTRUCTIONS) < 2800  # sent on every connection: keep it short


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
    text = research_text(tmp_path)
    msg = fails(server, "apply_org", blueprint=text, approved=True, plan_id=pid_of(server, text))
    assert "create_org" in msg and not target.exists()


def test_apply_org_with_errors_refuses_with_the_issues(setup, tmp_path):
    server, target = setup
    call(server, "create_org", mission="m")
    bad = research_text(tmp_path).replace("factcheck", "extra").replace("template: fact-checker", "template: researcher")
    msg = fails(server, "apply_org", blueprint=bad, approved=True, plan_id=blueprint_mod.plan_id(blueprint_mod.load_text(bad)))
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
