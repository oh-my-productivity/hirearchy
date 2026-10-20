# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.legacy.orgmcp.core import ROOT

ENG = "ceo/eng"


# ------------------------------------------------------------------------------------------ 6. grant hint
def test_delegable_arithmetic(org):
    org.send(ROOT, "ceo", "runs", budget=3)
    assert org.delegable("ceo") == (3, 0, 2)
    org.delegate("ceo", ENG, "t", "g", "c", budget=1)
    assert org.delegable("ceo") == (2, 1, 0)
    org.send(ROOT, "ceo", "more", budget=1)
    assert org.delegable("ceo") == (3, 1, 1)
    assert org.delegable(ENG) == (1, 0, 0)  # floor at 0


def test_grant_hint_says_plainly_when_the_recipient_cannot_delegate(org):
    org.send(ROOT, "ceo", "runs", budget=3)
    org.delegate("ceo", ENG, "t", "g", "c", budget=1)
    hint = org.grant_hint("ceo")
    assert hint == (
        "`ceo` now has 2 run(s) and 1 outstanding delegation(s): with 2 run(s) and 1 outstanding delegation(s) it "
        "cannot delegate anything; it can only process results or work itself - grant at least 1 more "
        "(a budget of 3) to allow one delegation of 1 run."
    )
    org.send(ROOT, "ceo", "more", budget=1)
    assert org.grant_hint("ceo") == "`ceo` now has 3 run(s) and 1 outstanding delegation(s); with one more delegation it can hand down at most 1 run(s)."


def test_grant_hint_needs_a_recipient_that_can_hire(org):
    org.send("ceo", ENG, "x")  # no budget, no hint needed
    assert org.grant_hint(ENG) == ""
