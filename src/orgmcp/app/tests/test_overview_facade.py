"""The overview slice of the ``Org`` facade: ``tree`` (the text of ``status``) behaves as it always did (green before and after), and now goes through
the port of the runtime (``org_tree``)."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org
from orgmcp.overview import OrgTree
from orgmcp.overview.testing import FixedOrgTree

BRIEF: dict[str, Any] = dict(
    description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}], acceptance=["Short"],
    deliverable={"description": "one file"}, budget=4,
)


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief executive", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    made.hire("root", "ops", "Operations", "Operate.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_a_new_organization_is_one_line(tmp_path: Path) -> None:
    assert Org.init(tmp_path / "fresh", "mission").tree() == "root (human): unread 0, delegated 0"


def test_the_tree_is_one_line_per_agent_below_the_root_line_indented_by_depth(org: Org) -> None:
    assert org.tree() == "\n".join([
        "root (human): unread 0, delegated 0",
        "  ceo [Chief executive] idle  budget=0 open=0 delegated=0 unread=0",
        "    eng [Engineer] idle  budget=0 open=0 delegated=0 unread=0",
        "  ops [Operations] idle  budget=0 open=0 delegated=0 unread=0",
    ])


def test_the_story_of_a_working_organization(org: Org) -> None:
    org.define_service("root", "ceo", "weekly-brief", **BRIEF)
    org.define_service("root", "ceo", "audit", **BRIEF)
    org.delegate("root", "ceo", "Plan", "Make a plan", "plan.md exists", budget=6)
    org.delegate("ceo", "ceo/eng", "Build", "Build it", "it builds", budget=2)
    org.pause("ops", "paused by the user: lunch")
    org.begin_run("ceo/eng")
    org.notify("root", "FYI", "a note")
    assert org.tree() == "\n".join([
        "root (human): unread 1, delegated 1",
        "  ceo [Chief executive] pending  budget=4 open=1 delegated=1 unread=1 services: audit, weekly-brief",
        "    eng [Engineer] running  budget=2 open=1 delegated=0 unread=0",
        "  ops [Operations] paused(paused by the user: lunch)  budget=0 open=0 delegated=0 unread=0",
    ])


def test_a_service_of_a_sibling_is_not_listed_on_the_line_of_an_agent_that_offers_none(org: Org) -> None:
    org.define_service("root", "ceo", "weekly-brief", **BRIEF)
    lines = org.tree().split("\n")
    assert lines[1].endswith(" services: weekly-brief") and "services:" not in lines[2] and "services:" not in lines[3]


def test_a_retired_service_is_no_longer_listed(org: Org) -> None:
    org.define_service("root", "ceo", "weekly-brief", **BRIEF)
    org.retire_service("root", "ceo", "weekly-brief", "done")
    assert "services:" not in org.tree()


# ----------------------------------------------------------------------------------- through the port of the runtime


def test_the_tree_is_the_text_of_the_port(org: Org) -> None:
    use(org, org_tree=FixedOrgTree("exactly this"))
    assert org.tree() == "exactly this"


def test_the_real_port_is_an_org_tree(org: Org) -> None:
    assert isinstance(org.runtime.org_tree, OrgTree)
