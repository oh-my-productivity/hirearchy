"""Contract of ``RunRegistry``: the ledger-backed registry and the in-memory fake keep the runs in flight the same way."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import JsonObject
from orgmcp.runs import RunRegistry
from orgmcp.runs.testing import IMPLEMENTATIONS, RunsHarness

from ._red import impls


@pytest.fixture(params=impls(IMPLEMENTATIONS[RunRegistry]), ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RunsHarness:
    made = cast(Callable[[Path], RunsHarness], request.param)(tmp_path)
    assert isinstance(made.registry, RunRegistry)
    return made


def rec(pgid: int, log: str = "ceo/runs/20261018T100000000001.log") -> JsonObject:
    return {"pgid": pgid, "lstart": "Sun Oct 18 10:00:00 2026", "started": 1_792_317_600.5, "scheduler": 4242, "log": log}


def test_a_registry_without_a_ledger_is_empty(h: RunsHarness) -> None:
    assert h.registry.all() == {}


def test_a_recorded_run_is_found_again(h: RunsHarness) -> None:
    h.registry.record("ceo", rec(111))
    assert h.registry.all() == {"ceo": rec(111)}


def test_the_values_keep_their_json_types(h: RunsHarness) -> None:
    record: JsonObject = {"pgid": 7, "lstart": None, "started": 12.25, "scheduler": 1, "log": "a/runs/x.log", "extra": [1, {"b": True}]}
    h.registry.record("a", record)
    assert h.registry.all() == {"a": record}


def test_recording_keeps_the_other_runs_and_replaces_the_same_agent(h: RunsHarness) -> None:
    h.registry.record("ceo", rec(111))
    h.registry.record("ceo/eng", rec(222))
    h.registry.record("ceo", rec(333))
    assert h.registry.all() == {"ceo": rec(333), "ceo/eng": rec(222)}


def test_entries_that_are_not_objects_are_dropped(h: RunsHarness) -> None:
    h.put_ledger('{"ceo": {"pgid": 1}, "gone/agent": "junk", "list": [1], "nothing": null, "number": 5}')
    assert h.registry.all() == {"ceo": {"pgid": 1}}


@pytest.mark.parametrize("text", ["", "not json at all", "[1, 2]", '"text"', "null", "{broken"])
def test_an_unreadable_ledger_is_an_empty_registry(h: RunsHarness, text: str) -> None:
    h.put_ledger(text)
    assert h.registry.all() == {}


def test_recording_into_an_unreadable_ledger_starts_afresh(h: RunsHarness) -> None:
    h.put_ledger("garbage")
    h.registry.record("ceo", rec(1))
    assert h.registry.all() == {"ceo": rec(1)}


def test_recording_leaves_malformed_entries_of_others_behind(h: RunsHarness) -> None:
    h.put_ledger('{"ceo": {"pgid": 1}, "junk": "x"}')
    h.registry.record("ceo/eng", rec(2))
    assert h.registry.all() == {"ceo": {"pgid": 1}, "ceo/eng": rec(2)}


def test_forgetting_removes_the_record(h: RunsHarness) -> None:
    h.registry.record("ceo", rec(1))
    h.registry.record("ceo/eng", rec(2))
    h.registry.forget("ceo")
    assert h.registry.all() == {"ceo/eng": rec(2)}


def test_forgetting_an_agent_that_has_no_record_changes_nothing(h: RunsHarness) -> None:
    h.registry.record("ceo", rec(1))
    h.registry.forget("nobody")
    h.registry.forget()
    assert h.registry.all() == {"ceo": rec(1)}


def test_forgetting_several_agents_removes_the_first_one_that_has_a_record_only(h: RunsHarness) -> None:
    """The scheduler's ``_forget_run`` has always stopped at the first hit (``any`` over a generator): a known quirk, kept as it is."""
    for pgid, addr in enumerate(("a", "b", "c"), start=1):
        h.registry.record(addr, rec(pgid))
    h.registry.forget("x", "b", "c")
    assert h.registry.all() == {"a": rec(1), "c": rec(3)}


def test_replacing_sets_all_records(h: RunsHarness) -> None:
    h.registry.record("ceo", rec(1))
    h.registry.replace({"ceo/eng": rec(2), "ops": rec(3)})
    assert h.registry.all() == {"ceo/eng": rec(2), "ops": rec(3)}


def test_replacing_with_nothing_empties_the_registry_and_it_stays_usable(h: RunsHarness) -> None:
    h.registry.record("ceo", rec(1))
    h.registry.replace({})
    assert h.registry.all() == {}
    h.registry.record("ops", rec(2))
    assert h.registry.all() == {"ops": rec(2)}


def test_the_records_handed_out_are_copies(h: RunsHarness) -> None:
    h.registry.record("ceo", rec(1))
    h.registry.all()["ceo"]["pgid"] = 999
    h.registry.all().pop("ceo")
    assert h.registry.all() == {"ceo": rec(1)}


def test_the_record_handed_in_is_copied(h: RunsHarness) -> None:
    record = rec(1)
    h.registry.record("ceo", record)
    record["pgid"] = 999
    mapping = {"ops": rec(2)}
    h.registry.replace(mapping)
    mapping["ops"]["pgid"] = 999
    assert h.registry.all() == {"ops": rec(2)}
