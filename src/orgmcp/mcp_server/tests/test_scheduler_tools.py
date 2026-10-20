# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio

import pytest
from testkit.legacy.orgmcp.core import ROOT
from testkit.mcp_server_world import StartRecorder, build_server, resolve_binding


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
def starts():
    """Stands for the patch point ``orgmcp.server.start_scheduler``: the starter the server's ``start`` tool calls."""
    return StartRecorder()


@pytest.fixture
def root_server(org, monkeypatch, starts):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    return build_server(*resolve_binding(), starts=starts)


def test_start_refuses_when_nothing_can_progress(org, stalled_on_budget, root_server, starts):
    starts.use(lambda *a: pytest.fail("must not start"))
    for until_done in (True, False):
        out = call(root_server, "start", until_done=until_done)
        assert out.startswith("not started: nothing can progress without you")
        assert 'needs budget (ceo out of runs)' in out and 'send(to="ceo", body="<why>", budget=N)' in out
    org.send(ROOT, "ceo", "more", budget=2)
    seen = {}
    starts.use(lambda m, u: seen.update(u=u) or 77)
    assert "scheduler started (pid 77" in call(root_server, "start") and seen == {"u": True}


def test_start_tool_description_mentions_the_waiting_exit(root_server):
    tools = {t.name: t.description for t in asyncio.run(root_server.list_tools())}
    assert "waiting for YOU" in tools["start"] and "start() refuses" in tools["start"]
