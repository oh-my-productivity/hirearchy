"""Contract of ``FailureCounter``: the ledger ``.runtime/failures.json`` of the real counter (on disk and in memory) and of the fake hold the same counts.

What the callers rely on: counts are per agent and survive in the file, ``clear`` forgets one agent, and ``repair`` makes a damaged ledger usable
again without touching a sound one."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.eligibility import FailureCounter
from hirearchy.eligibility.testing import IMPLEMENTATIONS, FailureHarness

from ._support import implementations


@pytest.fixture(params=implementations(IMPLEMENTATIONS[FailureCounter]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> FailureHarness:
    made = cast(Callable[[Path], FailureHarness], request.param)(tmp_path)
    assert isinstance(made.counter, FailureCounter)
    return made


def ledger(h: FailureHarness) -> object:
    text = h.text()
    assert text is not None
    return json.loads(text)


# ------------------------------------------------------------------------------ record / clear


def test_the_first_failure_is_one(h: FailureHarness) -> None:
    assert h.counter.record("ceo") == 1


def test_failures_in_a_row_are_counted(h: FailureHarness) -> None:
    assert [h.counter.record("ceo") for _ in range(3)] == [1, 2, 3]


def test_each_agent_has_its_own_count(h: FailureHarness) -> None:
    h.counter.record("ceo")
    h.counter.record("ceo")
    assert h.counter.record("ceo/eng") == 1 and ledger(h) == {"ceo": 2, "ceo/eng": 1}


def test_a_ledger_that_is_not_there_is_created(h: FailureHarness) -> None:
    assert h.text() is None
    h.counter.record("ceo")
    assert ledger(h) == {"ceo": 1}


def test_the_ledger_has_the_format_it_always_had(h: FailureHarness) -> None:
    h.counter.record("ceo")
    h.counter.record("ceo/eng")
    assert h.text() == json.dumps({"ceo": 1, "ceo/eng": 1}, indent=2) + "\n"


def test_the_count_goes_on_from_what_the_file_says(h: FailureHarness) -> None:
    h.put_text('{"ceo": 2}')
    assert h.counter.record("ceo") == 3


def test_clearing_forgets_one_agent(h: FailureHarness) -> None:
    h.counter.record("ceo")
    h.counter.record("ceo/eng")
    h.counter.clear("ceo")
    assert ledger(h) == {"ceo/eng": 1} and h.counter.record("ceo") == 1


def test_clearing_the_last_count_leaves_an_empty_ledger(h: FailureHarness) -> None:
    h.counter.record("ceo")
    h.counter.clear("ceo")
    assert h.text() == "{}\n"


def test_clearing_an_agent_without_a_count_writes_nothing(h: FailureHarness) -> None:
    h.counter.clear("ceo")
    assert h.text() is None
    h.put_text('{"ceo/eng": 1}')
    h.counter.clear("ceo")
    assert h.text() == '{"ceo/eng": 1}'


# ------------------------------------------------------------------------------ repair


def test_a_sound_ledger_is_not_repaired_nor_rewritten(h: FailureHarness) -> None:
    h.put_text('{"ceo":2,"ceo/eng":1}')
    assert h.counter.repair() is False
    assert h.text() == '{"ceo":2,"ceo/eng":1}'


def test_a_ledger_that_is_not_there_needs_no_repair(h: FailureHarness) -> None:
    assert h.counter.repair() is False and h.text() is None


@pytest.mark.parametrize("junk", ['"3"', "2.5", "[1]", "null", "true", '{"a": 1}', "[]"])
def test_an_entry_that_is_not_a_whole_number_is_dropped(h: FailureHarness, junk: str) -> None:
    h.put_text(f'{{"ceo": 2, "ceo/eng": {junk}}}')
    assert h.counter.repair() is True
    assert ledger(h) == {"ceo": 2}


def test_a_yes_or_no_is_not_a_count(h: FailureHarness) -> None:
    h.put_text('{"ceo": false, "ceo/eng": true, "ceo/qa": 0}')
    assert h.counter.repair() is True
    assert ledger(h) == {"ceo/qa": 0}


@pytest.mark.parametrize("junk", ["[]", "[1, 2]", "42", '"x"', "null", "true"])
def test_a_ledger_that_is_not_an_object_is_replaced_by_an_empty_one(h: FailureHarness, junk: str) -> None:
    h.put_text(junk)
    assert h.counter.repair() is True
    assert h.text() == "{}\n"


@pytest.mark.parametrize("junk", ["{ broken", "", "{"])
def test_a_ledger_that_cannot_be_parsed_is_left_alone(h: FailureHarness, junk: str) -> None:
    h.put_text(junk)
    assert h.counter.repair() is False
    assert h.text() == junk


def test_the_ledger_is_usable_after_it_was_repaired(h: FailureHarness) -> None:
    h.put_text('{"ceo": "many", "ceo/eng": 1}')
    h.counter.repair()
    assert h.counter.record("ceo") == 1 and h.counter.record("ceo/eng") == 2


def test_repairing_twice_changes_nothing_the_second_time(h: FailureHarness) -> None:
    h.put_text("[1]")
    assert h.counter.repair() is True
    assert h.counter.repair() is False
