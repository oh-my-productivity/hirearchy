"""``StatusTools``: status (the tree, with the scheduler line for root; the setup state) and health (own subtree only, unless root)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.access.testing import FixedModelFloorAudit
from hirearchy.daemon import SchedulerState
from hirearchy.daemon.testing import FakeSchedulerStatus
from hirearchy.kernel import ROOT
from hirearchy.mcp_server._instructions import InstructionText
from hirearchy.mcp_server._tools_status import StatusTools
from hirearchy.mcp_server._tools_identity import STALE_SKILL
from hirearchy.mcp_server.testing import FixedInstalledSkill, MemoryBinding, ScriptedHealth, agents_in
from hirearchy.overview.testing import FixedOrgTree

from ._support import call, fails, serve


STALE = Path("/h/.kiro/skills/hirearchy/SKILL.md")


NOTE = "Model floor: below the allowed models (claude-sonnet-5.5, claude-opus-5.5): ceo/eng on claude-haiku-4.5. Fix: set model: claude-sonnet-5.5 in each one's AGENT.md."


def tools(exists: bool = True, stale: Path | None = None, floor: str = "") -> tuple[StatusTools, ScriptedHealth]:
    agents, health = agents_in("ceo", "ceo/eng", "ops"), ScriptedHealth()
    return StatusTools(
        InstructionText(MemoryBinding(Path("/o"), exists=exists)), lambda: FixedOrgTree("THE TREE"),
        lambda: FakeSchedulerStatus(SchedulerState("running", 5, "then")), lambda: agents, lambda: health, lambda: health,
        FixedInstalledSkill(stale), lambda: FixedModelFloorAudit(note=floor),
    ), health


def test_an_agent_sees_the_tree_and_root_also_the_scheduler() -> None:
    assert call(serve(tools()[0], "ceo"), "status") == "THE TREE"
    assert call(serve(tools()[0], ROOT), "status") == "THE TREE\n\nscheduler: running (pid 5, since then)"


def test_root_is_told_when_the_installed_skill_is_out_of_date() -> None:
    out = call(serve(tools(stale=STALE)[0], ROOT), "status")
    assert out == "THE TREE\n\nscheduler: running (pid 5, since then)\n\n" + STALE_SKILL.format(path=STALE)
    assert "installed skill" not in call(serve(tools()[0], ROOT), "status")


def test_root_is_told_which_agents_run_below_the_model_floor() -> None:
    assert call(serve(tools(floor=NOTE)[0], ROOT), "status") == "THE TREE\n\nscheduler: running (pid 5, since then)\n\n" + NOTE
    out = call(serve(tools(stale=STALE, floor=NOTE)[0], ROOT), "status")
    assert out == "THE TREE\n\nscheduler: running (pid 5, since then)\n\n" + NOTE + "\n\n" + STALE_SKILL.format(path=STALE)  # the floor before the skill
    assert "Model floor" not in call(serve(tools()[0], ROOT), "status")


def test_an_agent_is_never_shown_the_floor_note() -> None:
    assert call(serve(tools(floor=NOTE)[0], "ceo"), "status") == "THE TREE"


def test_setup_mode_shows_no_floor_note() -> None:
    assert "Model floor" not in call(serve(tools(exists=False, floor=NOTE)[0], ROOT), "status")


def test_an_agent_never_sees_the_stale_skill_note_in_the_tree() -> None:
    assert call(serve(tools(stale=STALE)[0], "ceo"), "status") == "THE TREE"


def test_the_setup_state_also_carries_the_stale_skill_note() -> None:
    out = call(serve(tools(exists=False, stale=STALE)[0], ROOT), "status")
    assert out.startswith("Setup: no organization exists at /o yet.") and out.endswith("\n\n" + STALE_SKILL.format(path=STALE))


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
