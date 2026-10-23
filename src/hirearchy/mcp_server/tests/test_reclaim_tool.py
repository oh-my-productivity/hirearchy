# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

import pytest
from testkit.reach.hirearchy.core import ROOT
from testkit.mcp_server_world import build_server

ENG, QA = "ceo/eng", "ceo/qa"


def run(org, addr):
    org.begin_run(addr)
    org.start_run_log(addr)


def finish(org, addr):
    org.end_run(addr, ok=True)


@pytest.fixture
def team(org):
    """root gave ceo 12 runs; ceo gave eng 4 and qa 3. eng and qa have read their tasks and reported: idle, with runs left."""
    org.hire("ceo", "qa", "Tester", "Test things.")
    top = org.delegate(ROOT, "ceo", "Project", "goal", "criteria", budget=12)
    run(org, "ceo")
    a = org.delegate("ceo", ENG, "Build", "goal", "criteria", budget=4)
    b = org.delegate("ceo", QA, "Test", "goal", "criteria", budget=3)
    finish(org, "ceo")
    for addr, task in ((ENG, a), (QA, b)):
        run(org, addr)
        # reported "blocked" keeps the budget with the reporter (a final report would have returned it by itself)
        org.report(addr, task.id, "blocked", "waiting for a decision")
        finish(org, addr)
    run(org, "ceo")  # the blocked results woke ceo; it reads them
    finish(org, "ceo")
    assert (org.budget("ceo"), org.budget(ENG), org.budget(QA)) == (3, 3, 2)
    return top


def test_mcp_tool(team, org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(org, "ceo")
    tools = {t.name for t in asyncio.run(server.list_tools())}
    assert "reclaim" in tools
    out = asyncio.run(server.call_tool("reclaim", {"report": "eng", "budget": 2}))
    text = out[0][0].text if isinstance(out, tuple) else out[0].text
    assert text.startswith("reclaimed 2 run(s) from ceo/eng.") and f"Your budget is now {org.budget('ceo')}" in text
    root = build_server(org, ROOT)
    assert "reclaim" in {t.name for t in asyncio.run(root.list_tools())}


def test_skill_and_root_instructions_carry_the_reclaim_and_model_floor_rules():
    from testkit.mcp_server_world import skill_source

    from hirearchy.mcp_server._instructions import ROOT_INSTRUCTIONS

    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125 and len(ROOT_INSTRUCTIONS) < 2800
    for needle in ("every agent runs claude-sonnet-5.5 at high effort", "Nothing below claude-sonnet-5.5 at high effort is available",
                   "`reclaim(report=<agent>)`", "stranded runs", "never poll\n  with `sleep`"):
        assert needle in skill, needle
    for needle in ("models (all claude-sonnet-5.5 at high effort; nothing below is available)", "`reclaim`", "stranded runs"):
        assert needle in ROOT_INSTRUCTIONS, needle
    # the cheaper-models option is gone (D-E4-9): nothing offers tiers, a cheaper model or a lower effort
    assert "cheaper" not in ROOT_INSTRUCTIONS and "if cheaper" not in ROOT_INSTRUCTIONS
    assert "cheap/strong tiers" not in skill and "tiered\nmodels when asked" not in skill and "no tiers" not in skill
