# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.review_world import REVIEW_ACTIONS

ENG = "ceo/eng"


# ------------------------------------------------------------------------------------------ 2. review advice
def test_low_quality_advice_points_at_the_body_not_the_whole_charter():
    text = REVIEW_ACTIONS["low_quality"].format(a=ENG)
    assert "BODY of `ceo/eng`'s charter" in text and "kept automatically" in text
    assert "revises=<task id>" in text and "`revise_playbook`" in text and "tighten" not in text
    assert "frontmatter" in REVIEW_ACTIONS["expensive"]
