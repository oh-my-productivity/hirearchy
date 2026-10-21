# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.


def test_the_skill_sends_the_assistant_to_observe_instead_of_guessing():
    from testkit.skill_world import skill_source

    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125
    for needle in ("why something failed or took long, or what it cost", "use `observe` (read-only), never guesses",
                   '`view="trace"` with\n  the task id', '"now"', '"metrics"', "`errors_only=True`"):
        assert needle in skill, needle
