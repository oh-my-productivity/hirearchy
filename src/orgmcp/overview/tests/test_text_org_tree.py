"""``TextOrgTree``: what it asks of its collaborators, and nothing else."""

from __future__ import annotations

from pathlib import Path

from orgmcp.overview import OrgTree
from orgmcp.overview._tree import TextOrgTree
from orgmcp.overview.testing import OverviewWorld, memory_world


def world(tmp_path: Path) -> OverviewWorld:
    made = memory_world(tmp_path)
    assert isinstance(made.tree, TextOrgTree) and isinstance(made.tree, OrgTree)
    return made


def test_the_services_are_asked_of_the_agents_and_never_of_root(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.agent("ceo", "R")
    w.agent("ceo/eng", "R")
    w.tree.tree()
    assert w.services.asked == ["ceo", "ceo/eng"]


def test_an_agent_that_offers_no_service_has_no_suffix_at_all(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.agent("ceo", "R")
    w.offer("ceo", [])
    assert w.tree.tree().endswith("unread=0") and "services" not in w.tree.tree()


def test_a_service_list_is_joined_with_a_comma_and_a_space(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.agent("ceo", "R")
    w.offer("ceo", ["a", "b", "c"])
    assert w.tree.tree().endswith("unread=0 services: a, b, c")
