"""The texts of the server: the instructions of each identity (golden wording), their length, and the setup state."""

from __future__ import annotations

from pathlib import Path

from orgmcp.kernel import ROOT
from orgmcp.mcp_server._instructions import DS_STORE, INSTRUCTIONS, ROOT_INSTRUCTIONS, InstructionText
from orgmcp.mcp_server.testing import MemoryBinding

from ._support import red



@red
def test_the_instructions_of_an_agent_are_the_short_ones() -> None:
    text = InstructionText(MemoryBinding(Path("/o"), exists=True))
    assert text.for_identity("ceo") == INSTRUCTIONS and text.for_identity("ceo/eng") == INSTRUCTIONS
    assert INSTRUCTIONS.startswith("You are a member of a file-based organization of agents. Your identity is fixed by the runtime.")


@red
def test_root_instructions_name_the_organization_when_it_exists() -> None:
    out = InstructionText(MemoryBinding(Path("/o"), exists=True)).for_identity(ROOT)
    assert out == ROOT_INSTRUCTIONS.format(where="The organization is at /o.")


@red
def test_root_instructions_say_what_to_do_first_when_there_is_none() -> None:
    bound = InstructionText(MemoryBinding(Path("/o"))).for_identity(ROOT)
    assert "No organization exists at /o yet: the first step is create_org(mission=...), after which all tools work." in bound
    unbound = InstructionText(MemoryBinding(None)).for_identity(ROOT)
    assert "No organization exists and none is bound: the first step is create_org(mission=..., path=<absolute path>)" in unbound


@red
def test_root_instructions_are_sent_on_every_connection_so_they_stay_short() -> None:
    assert len(ROOT_INSTRUCTIONS) < 2700
    assert len(InstructionText(MemoryBinding(Path("/" + "x" * 200), exists=True)).for_identity(ROOT)) < 2900


def test_root_instructions_carry_the_workflow_and_the_safety_lines() -> None:
    for needle in ("ONE orgmcp organization as `root`", "never look for, create or modify another", "blueprint_example(kind)",
                   "propose_org", "apply_org(blueprint, approved=True, plan_id=<from propose_org>)", "progress(wait_seconds=N)",
                   "`reclaim`", "`observe` (read-only)", "start` ends by", "`stop` only if the user cancels"):
        assert needle in ROOT_INSTRUCTIONS, needle


@red
def test_the_setup_state_is_what_whoami_and_status_say_before_an_organization_exists() -> None:
    bound = InstructionText(MemoryBinding(Path("/o")))
    assert bound.active() and bound.state() == (
        "Setup: no organization exists at /o yet.\n"
        "Next step: call create_org(mission=\"...\") to create it; then hire a team, delegate work and start() the scheduler. "
        "Until then every other tool returns an error.\nscheduler: stopped")
    assert InstructionText(MemoryBinding(None)).state() == (
        "Setup: no organization exists (none found: ORG_ROOT is not set) yet.\n"
        "Next step: call create_org(mission=\"...\", path=<absolute path>) to create it; then hire a team, delegate work and start() the scheduler. "
        "Until then every other tool returns an error.\nscheduler: stopped")


@red
def test_setup_mode_ends_when_the_organization_exists() -> None:
    binding = MemoryBinding(Path("/o"))
    text = InstructionText(binding)
    assert text.active()
    binding.create("m")
    assert not text.active()


def test_finder_litter_has_a_name() -> None:
    assert DS_STORE == ".DS_Store"
