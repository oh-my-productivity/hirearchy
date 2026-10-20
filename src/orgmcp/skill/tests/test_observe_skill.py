# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.


def test_the_skill_sends_the_assistant_to_observe_instead_of_guessing():
    from orgmcp.skill import skill_source

    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125
    for needle in ("why something failed or took long, or what it cost", "use `observe` (read-only), never guesses",
                   '`view="trace"` with\n  the task id', '"now"', '"metrics"', "`errors_only=True`"):
        assert needle in skill, needle
