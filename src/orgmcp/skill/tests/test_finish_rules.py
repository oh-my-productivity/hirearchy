# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.skill_world import skill_source


# --------------------------------------------------------------------------------- skill and instructions
def test_skill_carries_the_finishing_rules():
    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125
    for needle in ("settle them with the user BEFORE you", "ask for approval", "state each one plainly",
                   "what happens if the check still fails after one rework",
                   "Ask at the FIRST budget request", "never wait until the reserve", "waiting on you",
                   "`start()` refuses until something changes", "declines more budget",
                   "unverified or partial result (say the task\n   stays open/blocked, not done)",
                   "shorter still when the user asks for a short answer", "one line per criterion",
                   "`stop()` only if the user cancels"):
        assert needle in skill, needle
