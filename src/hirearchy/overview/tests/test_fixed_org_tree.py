"""The fakes a consumer's test puts in place of the tree."""

from __future__ import annotations

from hirearchy.overview import OrgTree
from hirearchy.overview.testing import FixedOrgTree, FixedStates, NamedServices


def test_the_fixed_tree_is_its_text() -> None:
    fixed = FixedOrgTree("a\nb")
    assert isinstance(fixed, OrgTree) and fixed.tree() == "a\nb" and fixed.tree() == "a\nb"


def test_a_state_that_was_not_set_is_idle() -> None:
    states = FixedStates()
    states.words["ceo"] = "running"
    assert (states.state("ceo"), states.state("ops"), states.state("ceo/")) == ("running", "idle", "running")


def test_services_that_were_not_offered_are_none_and_every_question_is_kept() -> None:
    services = NamedServices()
    services.offered["ceo"] = ["x"]
    assert services.service_names("ceo") == ["x"] and services.service_names("ops") == [] and services.asked == ["ceo", "ops"]
