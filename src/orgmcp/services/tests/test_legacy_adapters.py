"""The old module-level functions of ``orgmcp.services`` are thin adapters of the ports of ``org.runtime`` (until step E3)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from orgmcp import services
from orgmcp.kernel import Message, OrgError
from orgmcp.services._host import ServicesOrg
from orgmcp.services.testing import ServicesWorld, memory_world

from ._support import BRIEF, STEPS, answer, define, populated, request


@pytest.fixture
def w(tmp_path: Path) -> ServicesWorld:
    return populated(memory_world(tmp_path))


def org_of(w: ServicesWorld) -> ServicesOrg:
    """What the old functions are given: an object with the ports in ``runtime`` (the facade is not importable here)."""
    runtime = SimpleNamespace(
        service_catalog=w.catalog, service_commands=w.commands, service_hints=w.hints, service_store=w.store, contract_normalizer=w.normalizer,
        rework_context=w.rework,
    )
    return SimpleNamespace(runtime=runtime, root=Path("/memory/org"), dir=lambda addr: Path("/memory/org") / addr)


def test_the_commands_are_those_of_the_port(w: ServicesWorld) -> None:
    org = org_of(w)
    text = services.define_service(org, "root", "ceo", "weekly-brief", **BRIEF)  # type: ignore[arg-type]
    assert text.startswith("defined service `weekly-brief` (contract v1) for ceo: ")
    task = services.request(org, "root", "weekly-brief", {"topic": "ai"}, title="T")
    assert (task.title, task.service) == ("T", "weekly-brief")
    assert services.revise_playbook(org, "ceo", "weekly-brief", STEPS, "first") == 1
    answer(w, task)
    assert services.feedback(org, "root", task.id, "reject", "Too long.").feedback == "reject"
    assert services.retire_service(org, "root", "ceo", "weekly-brief", "done").startswith("retired service `weekly-brief` of ceo; files kept at ")


def test_the_refusals_are_those_of_the_port(w: ServicesWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        services.define_service(org_of(w), "root", "ghost", "x", **BRIEF)  # type: ignore[arg-type]


def test_the_readers_are_those_of_the_catalog(w: ServicesWorld) -> None:
    org = org_of(w)
    define(w, playbook=STEPS)
    contract = services.read_contract(org, "ceo", "weekly-brief")
    assert contract is not None and contract == w.catalog.read_contract("ceo", "weekly-brief")
    assert services.read_playbook(org, "ceo", "weekly-brief").version == 1
    assert [c.name for c in services.owned_services(org, "ceo")] == ["weekly-brief"]
    assert [c.name for c in services.requestable_services(org, "root")] == ["weekly-brief"]
    assert services.read_contract(org, "ceo", "nope") is None


def test_the_hints_are_those_of_the_port(w: ServicesWorld) -> None:
    org = org_of(w)
    define(w)
    task = request(w)
    assert services.report_hint(org, "ceo", task, "done") == w.hints.report_hint("ceo", task, "done") != ""
    note = Message(sender="root", to="ceo", type="note", body=services.FEEDBACK_HEADER + "\n\nhello")
    assert services.feedback_text(note) == "hello"


def test_the_rework_fields_are_a_plain_dict_of_the_port(w: ServicesWorld) -> None:
    define(w)
    task = request(w)
    fields = services.rework_fields(org_of(w), "root", task.id)
    assert fields == {"service": "weekly-brief", "contract": 1, "playbook": 0} and type(fields) is dict
