# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.legacy.orgmcp.core import ROOT

ENG = "ceo/eng"


def test_qa18_delegate_without_budget_adapts_to_what_the_manager_can_afford(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    assert org.config["default_budget"] == 10
    org.delegate("ceo", ENG, "t", "g", "a")  # no budget given: an LLM manager does exactly this
