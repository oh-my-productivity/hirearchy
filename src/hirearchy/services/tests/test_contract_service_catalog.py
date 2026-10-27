"""Contract of ``ServiceCatalog``: the contracts and the playbooks read the same over disk and over memory.

What the callers rely on: a retired service is not listed, root offers none, a contract is parsed with the defaults of a missing field, the
playbook of a service that has none is version 0, and a client can request the services of its direct reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.services import ServiceCatalog
from hirearchy.services.testing import IMPLEMENTATIONS, ServicesWorld

from ._support import BRIEF, STEPS, STEPS_ITEMS, define, implementations, make, write_version


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceCatalog]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    made = make(request, tmp_path)
    assert isinstance(made.catalog, ServiceCatalog)
    return made


# ------------------------------------------------------------------------------ the names


def test_an_owner_without_services_offers_none(w: ServicesWorld) -> None:
    assert w.catalog.service_names("ceo") == []


def test_the_names_of_the_services_an_agent_offers_are_sorted(w: ServicesWorld) -> None:
    define(w, name="weekly-brief")
    define(w, name="daily-digest")
    assert w.catalog.service_names("ceo") == ["daily-digest", "weekly-brief"]


def test_root_offers_none(w: ServicesWorld) -> None:
    assert w.catalog.service_names("root") == [] and w.catalog.service_names("") == []


def test_a_retired_service_is_not_listed_any_more(w: ServicesWorld) -> None:
    define(w)
    define(w, name="other")
    w.commands.retire_service("root", "ceo", "weekly-brief", "not needed")
    assert w.catalog.service_names("ceo") == ["other"]
    assert w.catalog.read_contract("ceo", "weekly-brief") is None


def test_the_address_is_normalized(w: ServicesWorld) -> None:
    define(w)
    assert w.catalog.service_names("/ceo/") == ["weekly-brief"]


# ------------------------------------------------------------------------------ the contract


def test_there_is_no_contract_of_a_service_that_does_not_exist(w: ServicesWorld) -> None:
    assert w.catalog.read_contract("ceo", "nope") is None


def test_the_contract_is_what_was_defined(w: ServicesWorld) -> None:
    define(w, notes="Mind the sources.")
    c = w.catalog.read_contract("ceo", "weekly-brief")
    assert c is not None
    assert (c.name, c.owner, c.description, c.budget, c.locked, c.version) == ("weekly-brief", "ceo", BRIEF["description"], 10, False, 1)
    assert c.acceptance == BRIEF["acceptance"] and c.deliverable == BRIEF["deliverable"] and c.notes == "Mind the sources."
    assert c.inputs[1] == {"name": "week", "description": "ISO week; default the current one", "required": False}
    assert c.defined_by == "root" and c.defined is not None and c.created == c.defined
    assert c.path is not None and c.path.name == "SERVICE.md" and c.path.parent.name == "weekly-brief"


def test_the_creation_time_survives_an_amendment_but_the_definition_time_does_not(w: ServicesWorld) -> None:
    define(w)
    first = w.catalog.read_contract("ceo", "weekly-brief")
    w.commands.define_service("root", "ceo", "weekly-brief", budget=12)
    second = w.catalog.read_contract("ceo", "weekly-brief")
    assert first is not None and second is not None
    assert second.created == first.created and second.defined is not None and first.defined is not None and second.defined > first.defined


# ------------------------------------------------------------------------------ the playbook


def test_a_service_without_a_playbook_has_version_zero(w: ServicesWorld) -> None:
    define(w)
    pb = w.catalog.read_playbook("ceo", "weekly-brief")
    assert (pb.version, pb.body, pb.reason, pb.by, pb.revised, pb.path) == (0, "", "", "", None, None)


def test_the_playbook_is_the_current_version(w: ServicesWorld) -> None:
    define(w, playbook=STEPS)
    pb = w.catalog.read_playbook("ceo", "weekly-brief")
    assert (pb.version, pb.by, pb.reason, pb.body) == (1, "root", "initial playbook", STEPS_ITEMS)
    assert pb.revised is not None and pb.path is not None and pb.path.name == "PLAYBOOK.md"


# ------------------------------------------------------------------------------ who offers what


def test_the_services_an_agent_owns_are_listed_by_name(w: ServicesWorld) -> None:
    define(w, name="b-service")
    define(w, name="a-service")
    define(w, owner="ops", name="elsewhere")
    assert [c.name for c in w.catalog.owned_services("ceo")] == ["a-service", "b-service"]


def test_root_can_request_the_services_of_the_top_level_agents(w: ServicesWorld) -> None:
    define(w)
    define(w, owner="ops", name="ops-brief")
    assert [(c.owner, c.name) for c in w.catalog.requestable_services("root")] == [("ceo", "weekly-brief"), ("ops", "ops-brief")]


def test_a_manager_can_request_only_the_services_of_its_direct_reports(w: ServicesWorld) -> None:
    define(w)  # ceo's own: not requestable by ceo
    define(w, owner="ceo/eng", name="eng-brief", actor="ceo")
    assert [(c.owner, c.name) for c in w.catalog.requestable_services("ceo")] == [("ceo/eng", "eng-brief")]
    assert w.catalog.requestable_services("ceo/eng") == []


# ------------------------------------------------------------------------------ criteria and playbook versions


def test_criteria_of_a_service_carry_their_ids(w: ServicesWorld) -> None:
    define(w)
    w.commands.define_service(
        "root", "ceo", "weekly-brief", add_acceptance=["Dates are written in full"], remove_acceptance=["At most 600 words"], words="Dates in full, please.",
    )
    found = w.catalog.criteria("ceo", "weekly-brief")
    assert [(c.id, c.text, c.since, c.current, c.amended) for c in found] == [
        ("C1", "At most 600 words", 1, False, False),
        ("C2", "Every factual claim has a source URL", 1, True, False),
        ("C3", "Dates are written in full", 2, True, True),
    ]
    assert w.catalog.criteria("ceo", "no-such-service") == []


def test_criteria_carry_their_basis(w: ServicesWorld) -> None:
    define(w, acceptance=["A", "B"])
    write_version(w, 2, ["A", "B", "C"], answers="20261018T100000000012-root-0004", about="C1", words="Yes, add it.")
    write_version(w, 3, ["A", "B", "C", "D"], initiated="user", words="Add D.")
    found = w.catalog.criteria("ceo", "weekly-brief")
    assert [(c.id, c.since, c.answers, c.user) for c in found] == [
        ("C1", 1, "", False), ("C2", 1, "", False), ("C3", 2, "20261018T100000000012-root-0004", False), ("C4", 3, "", True),
    ]


def test_playbook_versions_are_oldest_first(w: ServicesWorld) -> None:
    define(w)
    assert w.catalog.playbook_versions("ceo", "weekly-brief") == []
    w.commands.revise_playbook("ceo", "weekly-brief", STEPS, "first", [])
    w.commands.revise_playbook("ceo", "weekly-brief", STEPS + "\n4. Publish.", "second", ["R1"])
    found = w.catalog.playbook_versions("ceo", "weekly-brief")
    assert [(p.version, p.reason) for p in found] == [(1, "first"), (2, "second")]
    assert found[0].body == STEPS and found[1].body.endswith("4. Publish.")


def test_read_playbook_of_an_item_file_gives_its_items(w: ServicesWorld) -> None:
    define(w)
    meta = {
        "service": "weekly-brief", "version": 1, "revised": "2026-01-02T00:00:00+00:00", "by": "ceo", "reason": "first", "op": "first",
        "admitted": "first", "items_max": 2, "rules": [], "why": {},
    }
    w.store.write_playbook("ceo", "weekly-brief", 1, meta, "## Steps\n1. [P1] Search.\n2. [P2] Write.", None)
    pb = w.catalog.read_playbook("ceo", "weekly-brief")
    assert pb.parse_error == "" and pb.items is not None and [(i.id, i.kind, i.text, i.section) for i in pb.items] == [
        ("P1", "step", "Search.", "## Steps"), ("P2", "step", "Write.", "## Steps"),
    ]
    assert pb.sections[0].heading == "## Steps" and pb.sections[0].numbered and pb.items_max == 2 and pb.op == "first"
    assert [p.items is not None for p in w.catalog.playbook_versions("ceo", "weekly-brief")] == [True]
    w.store.write_playbook("ceo", "weekly-brief", 2, {**meta, "version": 2}, "## Steps\n1. [P1] Search.\nstray", 1)
    broken = w.catalog.read_playbook("ceo", "weekly-brief")
    assert broken.items is None and broken.parse_error.startswith("line 3: ") and broken.version == 2  # read_playbook never raises
