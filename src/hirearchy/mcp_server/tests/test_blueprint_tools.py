# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio
import re
from pathlib import Path

import pytest
import testkit.reach.yaml as yaml
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.mcp_server_world import build_server, resolve_binding, skill_source
from testkit.mcp_server_world import blueprint as bp_mod
from testkit.blueprint_world import with_user_words, without_source_lines

from hirearchy.mcp_server._instructions import ROOT_INSTRUCTIONS

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
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
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
    """The template as the assistant uses it: its placeholders for the user's words filled in (a raw one is a draft: see test_provenance)."""
    return with_user_words(call(server, "blueprint_example", kind=kind))


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
    assert len(without_source_lines(b)) <= 42
    for needle in ("Goal:", "What I understood you need", "Team (4 agents)", "lead (Manager, model claude-sonnet-5.5)",
                   "Models: claude-sonnet-5.5 (high effort) for every agent", "reader", "can read files", "cannot change your files", "Budget: 19 runs planned",
                   "your cap is 25", "lead starts with 19", "Checking: reviewer", "Deliverable:", "Delivered to:",
                   str(env / "deliverables"), "(I copy it there after checking it)", "Done when ALL of these hold",
                   "1. Covers", "Checkpoints:", "Your files (read-only)", "approve"):
        assert needle in b, needle


def test_the_budget_question_comes_before_the_machine_marker(setup, tmp_path):
    """D-E7-3: the plan's budget question ends the block, so the assistant shows it with the rest."""
    from hirearchy.blueprint.tests.test_services import e5_blueprint

    server, _ = setup
    out = call(server, "propose_org", blueprint=yaml.safe_dump(e5_blueprint(tmp_path)))
    ask = "Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?"
    assert block(out).splitlines()[-1] == ask and out.index(ask) < out.index(bp_mod.PLAN_END)


def test_block_shows_a_code_workspace_and_write_access(setup, env):
    server, _ = setup
    b = block(call(server, "propose_org", blueprint=example(server, "code")))
    assert f"changes files only in {env / '<project-folder>'}" in b and "run commands" in b
    assert "Tests / packaging / commits" in b and len(without_source_lines(b)) <= 42
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
@pytest.mark.parametrize("kind", bp_mod.KINDS)
def test_every_example_validates_and_round_trips_through_propose_org(setup, kind):
    server, _ = setup
    text = example(server, kind)
    issues = bp_mod.validate(bp_mod.load_text(text))
    assert not bp_mod.errors(issues), [i.render() for i in issues]
    assert {i.code for i in issues} <= ALLOWED_WARNINGS, [i.render() for i in issues]
    out = call(server, "propose_org", blueprint=text)  # the whole returned text is valid YAML with a comment header
    assert bp_mod.PLAN_HEADING in out and plan_id_in(out)
    assert text.lstrip().startswith("# Blueprint schema in one paragraph")


def test_a_raw_template_is_a_draft_until_the_users_words_are_filled_in(setup):
    """Design 11.3: the quote and the recorded words of a template are placeholders; unfilled, the quote is not in the words (guard)."""
    server, _ = setup
    out = call(server, "propose_org", blueprint=call(server, "blueprint_example", kind="research"))
    assert bp_mod.PLAN_DRAFT_HEADING in out and "plan_id: none" in out
    assert "quotes words that are not in needs.elicitation: \"<THE USER'S EXACT WORDS>\"" in out


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
    for k in bp_mod.KINDS:
        assert k in msg


def test_example_works_in_setup_mode_and_is_the_default_research(setup):
    server, target = setup
    assert call(server, "blueprint_example") == call(server, "blueprint_example", kind="research") and not target.exists()


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


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)
