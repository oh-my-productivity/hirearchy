"""Finishing and naming: until-done exit when the user must act, the plan's failure policy and sentence-safe lines,
orgmcp vs built-in tool names in the prompts, stray org files in a workspace, and the skill/instruction rules."""

import asyncio

import pytest

from orgmcp.core import ROOT
from orgmcp.server import ROOT_INSTRUCTIONS, build_server, resolve_binding


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


# ------------------------------------------------------------------------------- until-done: waiting on the user
@pytest.fixture
def stalled_on_budget(org):
    """root's only task sits with ceo, which has used its single run: the task is unread and cannot be served."""
    task = org.delegate(ROOT, "ceo", "Rework the report", "Fix it", "It is fixed", budget=1)
    org.start_run_log("ceo")  # the one run is gone
    assert org.budget("ceo") == 0 and org.unread("ceo") == 1
    return task


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


def test_orgmcp_write_and_read_say_they_are_organization_tools(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    monkeypatch.setenv("ORG_AGENT", "ceo")
    server = build_server(*resolve_binding())
    tools = {t.name: t.description for t in asyncio.run(server.list_tools())}
    assert "ORGANIZATION file" in tools["write"] and "@orgmcp/write" in tools["write"] and "NOT kiro's built-in `write`" in tools["write"]
    assert "ORGANIZATION's read tool" in tools["read"] and "@orgmcp/read" in tools["read"]
    assert call(server, "write", path="ceo/MEMORY.md", content="notes") == "wrote ceo/MEMORY.md (organization file)"
    assert org.memory("ceo") == "notes"


def test_root_instructions_carry_the_finishing_rules_within_the_length_limit():
    for needle in ("settle its warnings (e.g. model policy) with the user", "or state them", "FIRST budget request",
                   "not after the reserve is gone", "declines", "unverified result (say the task stays open)",
                   "Final answer: as short as asked", "`stop` only if the user cancels"):
        assert needle in ROOT_INSTRUCTIONS, needle
    assert len(ROOT_INSTRUCTIONS) < 2800
