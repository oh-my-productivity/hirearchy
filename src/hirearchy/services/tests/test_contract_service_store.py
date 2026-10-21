"""Contract of ``ServiceStore``: the files of the services on disk and in memory answer alike.

What the callers rely on: a service is a directory of ``<owner>/services`` with a ``SERVICE.md``; a contract and a playbook round trip through their
frontmatter; the old version of either is kept as ``history/SERVICE.v<n>.md`` / ``history/PLAYBOOK.v<n>.md``; a retired service moves to
``services/.retired/<name>-<stamp>`` and is not listed any more."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.services import ServiceStore
from hirearchy.services.testing import IMPLEMENTATIONS, StoreHarness

from ._support import implementations


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceStore]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StoreHarness:
    made = cast(StoreHarness, request.param(tmp_path))
    assert isinstance(made.store, ServiceStore)
    return made


def contract(version: int = 1) -> dict[str, object]:
    return {"name": "brief", "description": "A brief.", "acceptance": ["Short"], "version": version, "budget": 3, "locked": False}


# ------------------------------------------------------------------------------ the names


def test_an_owner_without_services_has_no_names(h: StoreHarness) -> None:
    assert h.store.names("ceo") == []


def test_the_names_are_the_services_with_a_contract_sorted(h: StoreHarness) -> None:
    for name in ("weekly", "alpha", "monthly"):
        h.store.write_contract("ceo", name, contract(), "", None)
    assert h.store.names("ceo") == ["alpha", "monthly", "weekly"]


def test_a_directory_without_a_contract_is_not_a_service(h: StoreHarness) -> None:
    h.store.write_playbook("ceo", "orphan", 1, {"version": 1}, "Steps.")
    h.store.write_contract("ceo", "real", contract(), "", None)
    assert h.store.names("ceo") == ["real"]


def test_the_services_of_another_owner_are_not_listed(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "a", contract(), "", None)
    h.store.write_contract("ceo/eng", "b", contract(), "", None)
    assert h.store.names("ceo") == ["a"] and h.store.names("ceo/eng") == ["b"]


def test_root_offers_none(h: StoreHarness) -> None:
    h.store.write_contract("root", "x", contract(), "", None)
    assert h.store.names("root") == []


# ------------------------------------------------------------------------------ the contract


def test_a_missing_contract_or_playbook_is_none(h: StoreHarness) -> None:
    assert h.store.read_contract("ceo", "brief") is None and h.store.read_playbook("ceo", "brief") is None


def test_a_contract_round_trips_with_its_notes(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(), "Mind the sources.", None)
    meta, body = h.store.read_contract("ceo", "brief") or ({}, "")
    assert meta == contract() and body.strip() == "Mind the sources."


def test_writing_a_contract_returns_its_path_relative_to_the_organization(h: StoreHarness) -> None:
    assert h.store.write_contract("ceo", "brief", contract(), "", None) == "ceo/services/brief/SERVICE.md"
    assert h.text("ceo/services/brief/SERVICE.md") is not None


def test_the_file_is_the_frontmatter_and_the_body_with_one_trailing_newline(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", {"name": "brief", "version": 1}, "Notes.\n\n", None)
    assert h.text("ceo/services/brief/SERVICE.md") == "---\nname: brief\nversion: 1\n---\nNotes.\n"


def test_the_old_contract_is_kept_when_a_version_to_archive_is_named(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(1), "First.", None)
    first = h.text("ceo/services/brief/SERVICE.md")
    assert h.store.write_contract("ceo", "brief", contract(2), "Second.", 1) == "ceo/services/brief/SERVICE.md"
    assert h.text("ceo/services/brief/history/SERVICE.v1.md") == first
    meta, body = h.store.read_contract("ceo", "brief") or ({}, "")
    assert meta["version"] == 2 and body.strip() == "Second."


def test_nothing_is_kept_when_no_version_is_named(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(1), "", None)
    h.store.write_contract("ceo", "brief", contract(2), "", None)
    assert h.rels() == ["ceo/services/brief/SERVICE.md"]


# ------------------------------------------------------------------------------ the playbook


def test_a_playbook_round_trips(h: StoreHarness) -> None:
    meta = {"service": "brief", "version": 1, "by": "root", "reason": "initial playbook"}
    assert h.store.write_playbook("ceo", "brief", 1, meta, "## Steps\n1. Search.") == "ceo/services/brief/PLAYBOOK.md"
    assert h.store.read_playbook("ceo", "brief") == (meta, "## Steps\n1. Search.\n")


def test_the_old_playbook_is_kept_under_its_version(h: StoreHarness) -> None:
    h.store.write_playbook("ceo", "brief", 1, {"version": 1}, "One.")
    first = h.text("ceo/services/brief/PLAYBOOK.md")
    h.store.write_playbook("ceo", "brief", 2, {"version": 2}, "Two.", 1)
    assert h.text("ceo/services/brief/history/PLAYBOOK.v1.md") == first
    assert (h.store.read_playbook("ceo", "brief") or ({}, ""))[0]["version"] == 2


def test_the_history_of_the_playbook_is_the_kept_ones_then_the_current_one(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(), "", None)
    for version in (1, 2, 3):
        h.store.write_playbook("ceo", "brief", version, {"version": version, "revised": f"2026-01-0{version}T00:00:00+00:00"}, "Steps.", version - 1 or None)
    assert [v for v, _ in h.store.playbook_history("ceo", "brief")] == [1, 2, 3]
    assert [m["revised"] for _, m in h.store.playbook_history("ceo", "brief")][-1] == "2026-01-03T00:00:00+00:00"


def test_a_service_without_a_playbook_has_no_history(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(), "", None)
    assert h.store.playbook_history("ceo", "brief") == []


def test_a_playbook_without_a_version_is_version_zero(h: StoreHarness) -> None:
    h.store.write_playbook("ceo", "brief", 1, {"reason": "no version"}, "Steps.")
    assert h.store.playbook_history("ceo", "brief") == [(0, {"reason": "no version"})]


# ------------------------------------------------------------------------------ retiring


def test_a_retired_service_moves_under_the_retired_directory(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(), "", None)
    h.store.write_playbook("ceo", "brief", 1, {"version": 1}, "Steps.")
    assert h.store.retire("ceo", "brief", "20260101T000000000001") == "ceo/services/.retired/brief-20260101T000000000001"
    assert h.rels() == [
        "ceo/services/.retired/brief-20260101T000000000001/PLAYBOOK.md",
        "ceo/services/.retired/brief-20260101T000000000001/SERVICE.md",
    ]


def test_a_retired_service_is_not_listed_and_has_no_contract(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(), "", None)
    h.store.write_contract("ceo", "other", contract(), "", None)
    h.store.retire("ceo", "brief", "20260101T000000000001")
    assert h.store.names("ceo") == ["other"] and h.store.read_contract("ceo", "brief") is None


def test_a_service_of_the_same_name_can_be_defined_after_it_was_retired(h: StoreHarness) -> None:
    h.store.write_contract("ceo", "brief", contract(1), "", None)
    h.store.retire("ceo", "brief", "20260101T000000000001")
    h.store.write_contract("ceo", "brief", contract(1), "", None)
    assert h.store.names("ceo") == ["brief"] and len(h.rels()) == 2
