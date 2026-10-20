# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT, OrgError

ENG = "ceo/eng"


# ------------------------------------------------------------ default budget
def test_default_budget_is_capped_by_default_budget_setting(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=50)
    assert org.delegate("ceo", ENG, "t", "g", "a").budget == 10


def test_default_budget_is_what_is_affordable(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    msg = org.delegate("ceo", ENG, "t", "g", "a")
    assert msg.budget == 5 and org.budget("ceo") == 1  # 6 - (0 outstanding + 1)


def test_default_budget_reserves_a_run_per_outstanding_delegation(org):
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    org.delegate("ceo", ENG, "t", "g", "a", budget=2)  # 6 left, 1 outstanding
    msg = org.delegate("ceo", "ceo/ops", "t", "g", "a")
    assert msg.budget == 4  # 6 - (1 outstanding + 1 for this one)
    assert org.budget("ceo") == 2  # exactly the two reserved runs


def test_default_budget_below_one_explains_the_options(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)  # 2 left: 0 outstanding + 1 reserve = 1 affordable
    org.delegate("ceo", ENG, "t", "g", "a")
    org.hire("ceo", "ops", "Ops", "Do ops.")
    with pytest.raises(OrgError) as e:
        org.delegate("ceo", "ceo/ops", "t", "g", "a")
    text = str(e.value)
    assert "send" in text and "yourself" in text and "blocked" in text


def test_default_budget_with_exactly_the_reserve_left_fails(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=1)
    with pytest.raises(OrgError, match="cannot afford"):
        org.delegate("ceo", ENG, "t", "g", "a")


def test_root_default_budget_is_the_configured_default(org):
    assert org.delegate(ROOT, "ceo", "T", "g", "a").budget == org.config["default_budget"]


def test_explicit_budget_keeps_the_strict_check(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    with pytest.raises(OrgError, match="not enough budget"):
        org.delegate("ceo", ENG, "t", "g", "a", budget=6)
    assert org.delegate("ceo", ENG, "t", "g", "a", budget=5).budget == 5
    with pytest.raises(OrgError, match="at least 1"):
        org.delegate("ceo", ENG, "t", "g", "a", budget=0)
