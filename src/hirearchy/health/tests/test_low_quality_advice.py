# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.review_world import REVIEW_ACTIONS

ENG = "ceo/eng"


# ------------------------------------------------------------------------------------------ 2. review advice
def test_low_quality_advice_no_longer_sends_the_manager_to_the_charter():
    """Design 6.6: the charter and the model of an agent are the plan's, which the user changes; the advice keeps the evidence (escapes, the regression list)."""
    text = REVIEW_ACTIONS["low_quality"].format(a=ENG)
    assert "escapes" in text and "regression list" in text and "tighten" not in text
    assert "Its charter is the plan's: the retro brief shows the user these escapes." in text
    assert "BODY" not in text and "kept automatically" not in text and "replace it" not in text
    assert "revises=<task id>" not in text and "`revise_playbook`" not in text  # the advice no longer sends the manager to rework or revise
    assert "frontmatter" not in REVIEW_ACTIONS["expensive"] and "the plan's, which the user changes" in REVIEW_ACTIONS["expensive"]
    assert "charter" not in REVIEW_ACTIONS["wasteful"] and "change its model" not in REVIEW_ACTIONS["expensive"]
