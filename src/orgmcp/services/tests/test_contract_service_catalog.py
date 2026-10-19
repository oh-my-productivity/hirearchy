"""Contract of ``ServiceCatalog``: the contracts and the playbooks read the same over disk and over memory.

What the callers rely on: a retired service is not listed, root offers none, a contract is parsed with the defaults of a missing field, the
playbook of a service that has none is version 0, and a client can request the services of its direct reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.services import ServiceCatalog
from orgmcp.services.testing import IMPLEMENTATIONS, ServicesWorld

from ._support import BRIEF, define, implementations, make, RED, STEPS

pytestmark = RED


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
    assert (pb.version, pb.by, pb.reason, pb.body) == (1, "root", "initial playbook", STEPS)
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
