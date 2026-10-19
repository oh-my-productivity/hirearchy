"""``StoreReviewLedger``: ``.runtime/reviews.json`` over a ledger store, on disk and in memory."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orgmcp.kernel.testing import LedgerHarness, fs_ledger_store, memory_ledger_store
from orgmcp.review._ledger import StoreReviewLedger
from orgmcp.review._ports import LedgerRecord, ReviewLedger

from ._support import implementations

AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(params=implementations([fs_ledger_store, memory_ledger_store]))
def stores(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[ReviewLedger, LedgerHarness]:
    harness: LedgerHarness = request.param(tmp_path)
    ledger = StoreReviewLedger(harness.store)
    assert isinstance(ledger, ReviewLedger)
    return ledger, harness


def test_nothing_stored_reads_as_none(stores: tuple[ReviewLedger, LedgerHarness]) -> None:
    assert stores[0].read() is None


def test_what_is_saved_reads_back_normalised(stores: tuple[ReviewLedger, LedgerHarness]) -> None:
    ledger, _ = stores
    ledger.save(AT, 7, {"ceo": ["ceo/eng:idle"]})
    assert ledger.read() == LedgerRecord("2026-01-01T12:00:00+00:00", 7, {"ceo": ["ceo/eng:idle"]})


def test_the_ledger_is_written_with_its_keys_in_order_two_space_indented(stores: tuple[ReviewLedger, LedgerHarness]) -> None:
    ledger, harness = stores
    ledger.save(AT, 2, {})
    ledger.save(AT + timedelta(seconds=5, microseconds=700), 3, {"root": ["a:b"]})
    harness.put_raw("other", "x")
    assert harness.store.read("reviews") == {"at": "2026-01-01T12:00:05+00:00", "runs": 3, "notified": {"root": ["a:b"]}}
    assert list(harness.store.read("reviews")) == ["at", "runs", "notified"]  # seconds only: the microseconds are cut


def test_a_naive_time_is_saved_as_utc(stores: tuple[ReviewLedger, LedgerHarness]) -> None:
    ledger, _ = stores
    ledger.save(datetime(2026, 1, 1, 12, 0, 0), 0, {})
    assert ledger.read() == LedgerRecord("2026-01-01T12:00:00+00:00", 0, {})


@pytest.mark.parametrize("raw", ["not json", "[]", "{}", "3", ""])
def test_a_ledger_that_is_empty_or_not_an_object_reads_as_none(stores: tuple[ReviewLedger, LedgerHarness], raw: str) -> None:
    stores[1].put_raw("reviews", raw)
    assert stores[0].read() is None


def test_runs_that_are_not_an_int_count_as_zero_and_notified_keeps_only_lists(stores: tuple[ReviewLedger, LedgerHarness]) -> None:
    ledger, harness = stores
    for runs in (True, "7", 1.5, None):
        harness.put_raw("reviews", json.dumps({"at": "x", "runs": runs, "notified": {"a": ["k"], "b": "no", "c": 3}}))
        assert ledger.read() == LedgerRecord("x", 0, {"a": ["k"]})
    harness.put_raw("reviews", json.dumps({"runs": 4, "notified": ["not", "a", "mapping"]}))
    assert ledger.read() == LedgerRecord(None, 4, {})

