"""`reclaim`: a manager (or root) pulls unspent budget back from an idle direct report."""

import asyncio

import pytest

from orgmcp.core import ROOT
from orgmcp.server import build_server

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


def test_skill_and_root_instructions_carry_the_reclaim_and_cheap_model_rules():
    from orgmcp.server import ROOT_INSTRUCTIONS
    from orgmcp.skill import skill_source

    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125 and len(ROOT_INSTRUCTIONS) < 2800
    for needle in ("keep the lead (manager) and\n   the final verifier on the strong model", "the lead decides how every other run is spent",
                   "`reclaim(report=<agent>)`", "stranded runs", "never poll\n  with `sleep`"):
        assert needle in skill, needle
    for needle in ("keep the lead and final verifier", "the lead decides how every other run is spent", "`reclaim`", "stranded runs"):
        assert needle in ROOT_INSTRUCTIONS, needle
