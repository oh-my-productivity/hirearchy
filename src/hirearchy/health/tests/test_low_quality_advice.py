# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.review_world import REVIEW_ACTIONS

ENG = "ceo/eng"


# ------------------------------------------------------------------------------------------ 2. review advice
def test_low_quality_advice_points_at_the_body_not_the_whole_charter():
    text = REVIEW_ACTIONS["low_quality"].format(a=ENG)
    assert "BODY of `ceo/eng`'s charter" in text and "kept automatically" in text
    assert "escapes" in text and "regression list" in text and "tighten" not in text
    assert "revises=<task id>" not in text and "`revise_playbook`" not in text  # the advice no longer sends the manager to rework or revise
    assert "frontmatter" in REVIEW_ACTIONS["expensive"]
