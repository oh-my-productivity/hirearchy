"""The texts of the server: the instructions of each identity (golden wording), their length, and the setup state."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel import ROOT
from hirearchy.mcp_server._instructions import DS_STORE, INSTRUCTIONS, ROOT_INSTRUCTIONS, InstructionText
from hirearchy.mcp_server.testing import MemoryBinding




def test_the_instructions_of_an_agent_are_the_short_ones() -> None:
    text = InstructionText(MemoryBinding(Path("/o"), exists=True))
    assert text.for_identity("ceo") == INSTRUCTIONS and text.for_identity("ceo/eng") == INSTRUCTIONS
    assert INSTRUCTIONS.startswith("You are a member of a file-based organization of agents. Your identity is fixed by the runtime.")


def test_root_instructions_name_the_organization_when_it_exists() -> None:
    out = InstructionText(MemoryBinding(Path("/o"), exists=True)).for_identity(ROOT)
    assert out == ROOT_INSTRUCTIONS.format(where="The organization is at /o.")


def test_root_instructions_say_what_to_do_first_when_there_is_none() -> None:
    bound = InstructionText(MemoryBinding(Path("/o"))).for_identity(ROOT)
    assert "No organization exists at /o yet: the first step is create_org(mission=...), after which all tools work." in bound
    unbound = InstructionText(MemoryBinding(None)).for_identity(ROOT)
    assert "No organization exists and none is bound: the first step is create_org(mission=..., path=<absolute path>)" in unbound


def test_root_instructions_are_sent_on_every_connection_so_they_stay_short() -> None:
    assert len(ROOT_INSTRUCTIONS) < 2700
    assert len(InstructionText(MemoryBinding(Path("/" + "x" * 200), exists=True)).for_identity(ROOT)) < 2900


def test_root_instructions_carry_the_workflow_and_the_safety_lines() -> None:
    for needle in ("ONE hirearchy organization as `root`", "never look for, create or modify another", "blueprint_example(kind)",
                   "propose_org", "apply_org(blueprint, approved=True, plan_id=<from propose_org>)", "progress(wait_seconds=N)",
                   "`reclaim`", "`observe` (read-only)", "start` ends by", "`stop` only if the user cancels"):
        assert needle in ROOT_INSTRUCTIONS, needle


def test_root_instructions_name_the_skill_and_the_reject_order() -> None:
    """E4's s1r root never loaded the skill and amended before the reject was rated: the instructions say both, in one line each."""
    for needle in ("activate the hirearchy skill",
                   "On a reject: `feedback` first, then ONE yes/no question naming an id, then the change",
                   "send it back with\n   `request`/`delegate(..., revises=...)`",
                   "(no other paths or ORG_ROOT)"):
        assert needle in ROOT_INSTRUCTIONS, needle


def test_the_setup_state_is_what_whoami_and_status_say_before_an_organization_exists() -> None:
    bound = InstructionText(MemoryBinding(Path("/o")))
    assert bound.active() and bound.state() == (
        "Setup: no organization exists at /o yet.\n"
        "Next step: call create_org(mission=\"...\") to create it; then propose_org and apply_org a plan, and start() the scheduler. "
        "Until then every other tool returns an error.\nscheduler: stopped")
    assert InstructionText(MemoryBinding(None)).state() == (
        "Setup: no organization exists (none found: ORG_ROOT is not set) yet.\n"
        "Next step: call create_org(mission=\"...\", path=<absolute path>) to create it; then propose_org and apply_org a plan, and start() the scheduler. "
        "Until then every other tool returns an error.\nscheduler: stopped")


def test_setup_mode_ends_when_the_organization_exists() -> None:
    binding = MemoryBinding(Path("/o"))
    text = InstructionText(binding)
    assert text.active()
    binding.create("m")
    assert not text.active()


def test_finder_litter_has_a_name() -> None:
    assert DS_STORE == ".DS_Store"


def test_root_instructions_name_quality_on_its_own_line() -> None:
    """0b 9.1: one line after the reject line, `quality`: how the work went. The totals are the base 2565 / 2642 / 2782 plus its 32 characters; 2a (11.2) adds
    `; `retro` when due` (18 characters): 2597 / 2674 / 2814 become 2615 / 2692 / 2832."""
    reject = "  On a reject: `feedback` first, then ONE yes/no question naming an id, then the change (`define_service(answers=...)`).\n"
    assert reject + "  `quality`: how the work went; `retro` when due.\nWhen the user asks for an org, team or agents for a goal:\n" in ROOT_INSTRUCTIONS

    def sent(n: int) -> str:
        return InstructionText(MemoryBinding(Path("/" + "r" * n), exists=True)).for_identity(ROOT)

    lines = ROOT_INSTRUCTIONS.splitlines()
    assert (len(ROOT_INSTRUCTIONS), len(sent(59)), len(sent(199)), len(lines), max(map(len, lines))) == (2615, 2692, 2832, 27, 120)
