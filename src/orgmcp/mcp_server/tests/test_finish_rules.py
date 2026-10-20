# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from orgmcp.mcp_server._instructions import ROOT_INSTRUCTIONS


def test_root_instructions_carry_the_finishing_rules_within_the_length_limit():
    for needle in ("settle its warnings (e.g. model policy) with the user", "or state them", "FIRST budget request",
                   "not after the reserve is gone", "declines", "unverified result (say the task stays open)",
                   "Final answer: as short as asked", "`stop` only if the user cancels"):
        assert needle in ROOT_INSTRUCTIONS, needle
    assert len(ROOT_INSTRUCTIONS) < 2800
