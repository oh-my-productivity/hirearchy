"""``StatusTools``: status (the tree, with the scheduler line for root; the setup state) and health (own subtree only, unless root)."""

from __future__ import annotations

from pathlib import Path

from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.kernel import ROOT
from orgmcp.mcp_server._instructions import InstructionText
from orgmcp.mcp_server._tools_status import StatusTools
from orgmcp.mcp_server.testing import MemoryBinding, ScriptedHealth, agents_in
from orgmcp.overview.testing import FixedOrgTree

from ._support import call, fails, serve


def tools(exists: bool = True) -> tuple[StatusTools, ScriptedHealth]:
    agents, health = agents_in("ceo", "ceo/eng", "ops"), ScriptedHealth()
    return StatusTools(
        InstructionText(MemoryBinding(Path("/o"), exists=exists)), lambda: FixedOrgTree("THE TREE"),
        lambda: FakeSchedulerStatus(SchedulerState("running", 5, "then")), lambda: agents, lambda: health, lambda: health,
    ), health


def test_an_agent_sees_the_tree_and_root_also_the_scheduler() -> None:
    assert call(serve(tools()[0], "ceo"), "status") == "THE TREE"
    assert call(serve(tools()[0], ROOT), "status") == "THE TREE\n\nscheduler: running (pid 5, since then)"


def test_before_the_organization_exists_root_gets_the_setup_state() -> None:
    assert call(serve(tools(exists=False)[0], ROOT), "status").startswith("Setup: no organization exists at /o yet.")


def test_health_defaults_to_the_callers_own_subtree_and_to_the_whole_organization_for_root() -> None:
    group, health = tools()
    assert call(serve(group, "ceo"), "health") == "HEALTH of ceo"
    assert call(serve(group, ROOT), "health") == "HEALTH of root"
    assert health.asked == ["ceo", "root"]


def test_an_agent_may_look_at_itself_and_its_subtree_only() -> None:
    group, health = tools()
    assert call(serve(group, "ceo"), "health", agent="ceo/eng") == "HEALTH of ceo/eng"
    assert "you can only view health for yourself or agents in your own subtree (ceo/...), not ops" in fails(serve(group, "ceo"), "health", agent="ops")
    assert health.asked == ["ceo/eng"]


def test_root_may_ask_about_anyone_and_an_unknown_agent_is_refused() -> None:
    group, _ = tools()
    assert call(serve(group, ROOT), "health", agent="ops") == "HEALTH of ops"
    assert "no such agent: nobody" in fails(serve(group, ROOT), "health", agent="nobody")
