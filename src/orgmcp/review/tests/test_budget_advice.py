# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from datetime import timedelta

import pytest
from testkit.legacy.orgmcp.core import ROOT, utcnow
from testkit.review_world import REVIEW_ACTIONS, review

ENG = "ceo/eng"


# ---------------------------------------------------------------------------- stranded_budget
def later(hours):
    return utcnow() + timedelta(hours=hours)


@pytest.fixture
def stranded(org):
    """eng holds 3 runs, nothing to do, and its parent (ceo) is not root."""
    org.send(ROOT, "ceo", "grant", budget=10)
    org.send("ceo", ENG, "grant", budget=3)
    for a in ("ceo", ENG):
        org.begin_run(a)
        org.end_run(a, ok=True)  # both read their grant: no unread mail
    return org


def test_the_review_tells_the_manager_what_to_do(stranded):
    result = review(stranded, now=later(1))
    ceo_note = next(n for n in result.notes if n.to == "ceo")
    assert "`ceo/eng` stranded_budget" in ceo_note.body
    assert REVIEW_ACTIONS["stranded_budget"].format(a=ENG) in ceo_note.body
    assert "return its budget" in ceo_note.body and "retire" in ceo_note.body
