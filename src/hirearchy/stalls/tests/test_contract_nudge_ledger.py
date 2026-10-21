"""Contract of ``NudgeLedger`` (and of the recorder that writes it): ``.runtime/nudges.json`` of the real ledger over a file, over a ledger in memory,
and of the fake hold the same entries and the same bytes, and a legacy or a damaged ledger never raises."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.stalls import NudgeLedger
from hirearchy.stalls.testing import IMPLEMENTATIONS, NudgesHarness

from ._support import make_nudges


@pytest.fixture(params=IMPLEMENTATIONS[NudgeLedger], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> NudgesHarness:
    made = make_nudges(request, tmp_path)
    assert isinstance(made.ledger, NudgeLedger)
    return made


def task(sender: str) -> Message:
    return Message(sender=sender, to="x", type="task", title="T", body="b", id="T-1")


# ------------------------------------------------------------------------------ entries


def test_there_are_no_entries_without_a_ledger(h: NudgesHarness) -> None:
    assert h.ledger.entries() == {} and h.text() is None


def test_the_entries_are_what_the_ledger_holds(h: NudgesHarness) -> None:
    h.put_text('{"T-1": {"step": 1, "at": 1700000000.5}, "T-2": {"step": 0, "at": 0}}')
    assert h.ledger.entries() == {"T-1": {"step": 1, "at": 1700000000.5}, "T-2": {"step": 0, "at": 0}}


def test_the_legacy_ledger_reads_as_steps(h: NudgesHarness) -> None:
    h.put_text('{"T-1": "nudged", "T-2": "escalated", "T-3": "anything else"}')
    assert h.ledger.entries() == {"T-1": {"step": 0, "at": 0}, "T-2": {"step": 1, "at": 0}, "T-3": {"step": 1, "at": 0}}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"a": {"step": "2", "at": "12"}}', {"a": {"step": 2, "at": 12.0}}),  # numbers in text are numbers
        ('{"a": {"step": 1.9, "at": 3}}', {"a": {"step": 1, "at": 3.0}}),
        ('{"a": {"step": -3, "at": 3}}', {"a": {"step": 0, "at": 3.0}}),  # no step before the first
        ('{"a": {"step": 1}}', {"a": {"step": 1, "at": 0.0}}),  # no time: the epoch
        ('{"a": {"step": 1, "at": null}}', {"a": {"step": 1, "at": 0.0}}),
    ],
)
def test_the_fields_of_an_entry_are_read_as_numbers(h: NudgesHarness, raw: str, expected: dict[str, dict[str, float]]) -> None:
    h.put_text(raw)
    assert h.ledger.entries() == expected


@pytest.mark.parametrize(
    "junk",
    ['{"a": []}', '{"a": 3}', '{"a": null}', '{"a": {"step": "x"}}', '{"a": {"at": 3}}', '{"a": {"step": null}}', '{"a": {"step": 1, "at": "soon"}}'],
)
def test_a_malformed_entry_is_dropped_and_the_others_are_kept(h: NudgesHarness, junk: str) -> None:
    h.put_text(junk[:-1] + ', "ok": {"step": 1, "at": 5}}')
    assert h.ledger.entries() == {"ok": {"step": 1, "at": 5}}


@pytest.mark.parametrize("junk", ["[]", "42", '"x"', "null", "true", "{ broken", "", "\x00"])
def test_a_malformed_ledger_has_no_entries_and_never_raises(h: NudgesHarness, junk: str) -> None:
    h.put_text(junk)
    assert h.ledger.entries() == {}


# ------------------------------------------------------------------------------ chain


def test_the_chain_of_a_task_from_root_is_the_assignee_and_root(h: NudgesHarness) -> None:
    h.put_agent("ceo")
    assert h.ledger.chain("ceo", task("root")) == ["ceo", "root"]


def test_the_chain_goes_from_the_assignee_to_the_assigner_and_up_to_root(h: NudgesHarness) -> None:
    for addr in ("ceo", "ceo/eng", "ceo/eng/dev"):
        h.put_agent(addr)
    assert h.ledger.chain("ceo/eng/dev", task("ceo/eng")) == ["ceo/eng/dev", "ceo/eng", "ceo", "root"]
    assert h.ledger.chain("ceo/eng/dev", task("ceo")) == ["ceo/eng/dev", "ceo", "root"]  # the assigner is not the parent: the chain follows the assigner


def test_a_sibling_as_assigner_is_told_before_its_own_ancestors(h: NudgesHarness) -> None:
    for addr in ("ceo", "ceo/eng", "ops", "ops/lead"):
        h.put_agent(addr)
    assert h.ledger.chain("ceo/eng", task("ops/lead")) == ["ceo/eng", "ops/lead", "ops", "root"]


def test_the_chain_follows_the_parent_when_the_assigner_is_gone(h: NudgesHarness) -> None:
    for addr in ("ceo", "ceo/eng"):
        h.put_agent(addr)
    assert h.ledger.chain("ceo/eng", task("ghost")) == ["ceo/eng", "ceo", "root"]


def test_the_chain_of_a_top_level_assignee_whose_assigner_is_gone_ends_at_root(h: NudgesHarness) -> None:
    h.put_agent("ceo")
    assert h.ledger.chain("ceo", task("ghost")) == ["ceo", "root"]


# ------------------------------------------------------------------------------ save


def test_saving_writes_the_ledger_in_the_format_it_always_had(h: NudgesHarness) -> None:
    entries = {"T-1": {"step": 1, "at": 1700000000.5}}
    h.recorder.save(entries)
    assert h.text() == json.dumps(entries, indent=2) + "\n"
    assert h.ledger.entries() == entries


def test_saving_replaces_the_ledger(h: NudgesHarness) -> None:
    h.recorder.save({"T-1": {"step": 0, "at": 1.0}})
    h.recorder.save({"T-2": {"step": 1, "at": 2.0}})
    assert h.ledger.entries() == {"T-2": {"step": 1, "at": 2.0}}


def test_saving_what_the_ledger_holds_writes_nothing(h: NudgesHarness) -> None:
    h.put_text('{"T-1":{"step":0,"at":1.0}}')  # not the layout the recorder writes: a rewrite would show
    h.recorder.save({"T-1": {"step": 0, "at": 1.0}})
    assert h.text() == '{"T-1":{"step":0,"at":1.0}}'


def test_no_entries_and_no_ledger_write_no_file(h: NudgesHarness) -> None:
    h.recorder.save({})
    assert h.text() is None


def test_the_legacy_ledger_is_replaced_by_the_current_form(h: NudgesHarness) -> None:
    h.put_text('{"T-1": "nudged"}')
    h.recorder.save(h.ledger.entries())
    assert json.loads(h.text() or "") == {"T-1": {"step": 0, "at": 0}}


def test_dropped_entries_are_dropped_from_the_file(h: NudgesHarness) -> None:
    h.put_text('{"T-1": {"step": "x"}, "T-2": {"step": 1, "at": 5}}')
    h.recorder.save(h.ledger.entries())
    assert json.loads(h.text() or "") == {"T-2": {"step": 1, "at": 5}}


@pytest.mark.parametrize("junk", ["[]", "42", '"x"', "null"])
def test_a_ledger_that_is_not_an_object_is_replaced_even_by_nothing(h: NudgesHarness, junk: str) -> None:
    h.put_text(junk)
    h.recorder.save({})
    assert h.text() == "{}\n"


def test_a_ledger_that_cannot_be_parsed_is_left_alone_when_there_is_nothing_to_save(h: NudgesHarness) -> None:
    h.put_text("{ broken")
    h.recorder.save({})
    assert h.text() == "{ broken"
