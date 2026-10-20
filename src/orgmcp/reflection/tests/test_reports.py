# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.services_world import svc


def test_status_tree_names_the_services_an_agent_offers(svc):
    tree = svc.tree()
    assert "ceo [Chief executive]" in tree and " services: weekly-brief" in tree.split("\n")[1]
    assert "services:" not in tree.split("\n")[2]
