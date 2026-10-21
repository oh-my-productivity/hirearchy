# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.services_world import svc


def test_status_tree_names_the_services_an_agent_offers(svc):
    tree = svc.tree()
    assert "ceo [Chief executive]" in tree and " services: weekly-brief" in tree.split("\n")[1]
    assert "services:" not in tree.split("\n")[2]


def test_the_services_listing_shows_criteria_by_id(svc):
    from testkit.reach.hirearchy.core import ROOT

    svc.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=["Never longer than one page"], remove_acceptance=["At most 600 words"])
    for who in (ROOT, "ceo"):
        out = svc.runtime.service_reports.services_text(who)
        assert "    C2: Every factual claim has a source URL\n    C3: Never longer than one page\n  record:" in out
        assert "C1" not in out and "1. " not in out.split("record:")[0]  # the removed C1 is not listed, and nothing is numbered by position
