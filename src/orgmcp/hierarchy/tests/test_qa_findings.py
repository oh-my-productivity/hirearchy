# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.orgmcp.core import ROOT, OrgError

ENG = "ceo/eng"


# ----------------------------------------------------------- budget and reviews
def test_qa6_retire_returns_unspent_budget_to_the_parent(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=5)
    assert org.budget("ceo") == 5
    org.retire("ceo", "eng", "not needed")
    assert org.budget("ceo") == 10


# --------------------------------------------------------------------- core API
def test_qa9_retire_accepts_the_full_address_of_a_direct_report(org):
    assert org.retire("ceo", ENG, "full address, as printed by status/health/review notes") == ENG


def test_qa11_hire_rejects_name_with_trailing_newline(org):
    with pytest.raises(OrgError):
        org.hire("ceo", "ops\n", "Ops", "Do ops.")
