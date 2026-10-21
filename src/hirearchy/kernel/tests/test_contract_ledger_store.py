"""Contract of ``LedgerStore`` (``.runtime/<name>.json``): the real store and the in-memory one."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import JsonObject, LedgerStore
from hirearchy.kernel.testing import IMPLEMENTATIONS, LedgerHarness


@pytest.fixture(params=IMPLEMENTATIONS[LedgerStore], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> LedgerHarness:
    made = cast(Callable[[Path], LedgerHarness], request.param)(tmp_path)
    assert isinstance(made.store, LedgerStore)
    return made


def test_a_ledger_that_was_never_written_is_empty(h: LedgerHarness) -> None:
    assert h.store.read("failures") == {}


def test_what_was_written_is_read_back(h: LedgerHarness) -> None:
    data: JsonObject = {"ceo": 2, "ceo/eng": 0, "names": ["é", "✓"], "nested": {"a": {"b": None}}, "flag": True, "ratio": 0.5}
    h.store.write("failures", data)
    assert h.store.read("failures") == data


def test_a_write_replaces_the_whole_ledger(h: LedgerHarness) -> None:
    h.store.write("nudges", {"a": 1, "b": 2})
    h.store.write("nudges", {"c": 3})
    assert h.store.read("nudges") == {"c": 3}


def test_ledgers_are_independent(h: LedgerHarness) -> None:
    h.store.write("failures", {"x": 1})
    h.store.write("strays", {"y": 2})
    assert (h.store.read("failures"), h.store.read("strays"), h.store.read("reviews")) == ({"x": 1}, {"y": 2}, {})


def test_an_empty_ledger_can_be_written(h: LedgerHarness) -> None:
    h.store.write("failures", {"x": 1})
    h.store.write("failures", {})
    assert h.store.read("failures") == {}


@pytest.mark.parametrize("raw", ["", "not json", "{\"a\": ", "\x00\x01", "[1, 2]", "42", "null", "\"text\""])
def test_an_unreadable_or_non_object_ledger_reads_as_empty(h: LedgerHarness, raw: str) -> None:
    h.put_raw("failures", raw)
    assert h.store.read("failures") == {}


def test_a_ledger_can_be_rewritten_after_corruption(h: LedgerHarness) -> None:
    h.put_raw("failures", "garbage")
    h.store.write("failures", {"ok": 1})
    assert h.store.read("failures") == {"ok": 1}


def test_what_is_read_is_a_copy(h: LedgerHarness) -> None:
    h.store.write("failures", {"n": {"a": 1}})
    first = h.store.read("failures")
    first["n"] = "changed"
    first["extra"] = 1
    assert h.store.read("failures") == {"n": {"a": 1}}
