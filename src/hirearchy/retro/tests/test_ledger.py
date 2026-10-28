"""``LedgerRetroRecords``: ``.runtime/retros.json`` over a ledger store, on disk and in memory (design 4.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hirearchy.kernel import JsonObject, LedgerStore, OrgError, OrgPaths
from hirearchy.kernel.testing import LedgerHarness, MemoryLedgerStore, fs_ledger_store, memory_ledger_store
from hirearchy.retro import ASKED_KEPT, RECORDS_KEPT, RecordedItem, RetroRecords
from hirearchy.retro._ledger import LEDGER, LedgerRetroRecords

from ._records import ORIGIN, record


@pytest.fixture(params=[fs_ledger_store, memory_ledger_store], ids=lambda factory: factory.__name__)
def stores(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[RetroRecords, LedgerHarness]:
    harness: LedgerHarness = request.param(tmp_path)
    made = LedgerRetroRecords(harness.store)
    assert isinstance(made, RetroRecords)
    return made, harness


def stored(harness: LedgerHarness) -> JsonObject:
    return harness.store.read(LEDGER)


def briefs_of(harness: LedgerHarness) -> list[dict[str, object]]:
    briefs = stored(harness)["briefs"]
    assert isinstance(briefs, list)
    return briefs


def test_the_ledger_is_named_retros_and_is_the_file_of_that_name(tmp_path: Path) -> None:
    assert LEDGER == "retros" and OrgPaths(tmp_path).ledger_file(LEDGER) == tmp_path / ".runtime" / "retros.json"


def test_nothing_stored_reads_as_nothing(stores: tuple[RetroRecords, LedgerHarness]) -> None:
    records, _ = stores
    assert records.last() is None and records.records() == () and records.asked() == frozenset()


def test_append_then_last_and_records_oldest_first(stores: tuple[RetroRecords, LedgerHarness]) -> None:
    records, harness = stores
    records.append(record(1, "a"))
    records.append(record(2, "b"))
    assert [r.id for r in records.records()] == ["B1", "B2"] and records.last() == record(2, "b")
    assert [b["id"] for b in briefs_of(harness)] == ["B1", "B2"]


def test_records_keep_the_newest_50(stores: tuple[RetroRecords, LedgerHarness]) -> None:
    records, harness = stores
    for n in range(1, RECORDS_KEPT + 3):
        records.append(record(n))
    briefs = briefs_of(harness)
    assert len(briefs) == RECORDS_KEPT
    assert briefs[0]["id"] == "B3" and briefs[-1]["id"] == f"B{RECORDS_KEPT + 2}"


def test_asked_keeps_every_key_once_and_at_most_1000(stores: tuple[RetroRecords, LedgerHarness]) -> None:
    records, harness = stores
    records.append(record(1, "a", "b"))
    records.append(record(2, "b", "c"))
    assert stored(harness)["asked"] == ["a", "b", "c"]  # a key offered again is moved to the newest end: here "b" was already there
    for n in range(3, 3 + ASKED_KEPT // 3 + 5):
        records.append(record(n, f"p{n}a", f"p{n}b", f"p{n}c"))
    asked = stored(harness)["asked"]
    assert isinstance(asked, list) and len(asked) == ASKED_KEPT and len(set(asked)) == ASKED_KEPT and asked[-1].startswith("p")


def test_a_key_offered_again_is_listed_after_the_keys_that_came_between(stores: tuple[RetroRecords, LedgerHarness]) -> None:
    records, harness = stores
    records.append(record(1, "a", "b"))
    records.append(record(2, "c"))
    records.append(record(3, "a"))
    assert stored(harness)["asked"] == ["b", "c", "a"]


def test_a_record_holds_ids_and_keys_only(stores: tuple[RetroRecords, LedgerHarness]) -> None:
    records, harness = stores
    records.append(record(2, "service|lead|M1", lapsed=1))
    data = stored(harness)
    assert set(data) == {"briefs", "asked"}
    assert data["briefs"] == [{
        "id": "B2", "at": "2026-11-04T09:40:05+00:00", "since": "2026-11-03T09:40:05+00:00", "by": "mcp",
        "items": [{"n": 1, "kind": "service", "key": "service|lead|M1", "evidence": ["E2-1"], "effect": {"service": "lead/service|lead|M1"}, "lapsed": 1}],
        "held_back": ["held|2"],
    }]
    records.append(record(1))  # a record with no window start writes null
    assert [b["since"] for b in briefs_of(harness)] == ["2026-11-03T09:40:05+00:00", None]


def test_no_text_of_the_client_or_the_team_can_reach_the_ledger() -> None:
    fields = set(RecordedItem.__dataclass_fields__)
    assert fields == {"n", "kind", "key", "evidence", "effect", "lapsed"}  # the question, the call and the cost are not kept


def test_an_unwritable_ledger_raises_org_error(tmp_path: Path) -> None:
    class Full(LedgerStore):
        def read(self, name: str) -> JsonObject:
            return {}

        def write(self, name: str, data: JsonObject) -> None:
            raise OSError(28, "No space left on device")

    records = LedgerRetroRecords(Full())
    with pytest.raises(OrgError, match=r"retros\.json.*No space left on device"):
        records.append(record(1, "a"))


@pytest.mark.parametrize("data", [
    {"briefs": 5}, {"briefs": ["x"]}, {"briefs": [{"id": "B1"}]}, {"briefs": [], "asked": "a"}, {"briefs": [], "asked": [1]},
    {"briefs": [{"id": "B1", "at": "yesterday", "since": None, "by": "mcp", "items": [], "held_back": []}]},
    {"briefs": [{"id": "B1", "at": "2026-11-03T09:40:05+00:00", "since": None, "by": "mcp", "items": [{"n": "one"}], "held_back": []}]},
])
def test_a_ledger_that_is_not_a_ledger_of_briefs_is_unreadable_and_the_next_append_replaces_it(data: JsonObject) -> None:
    store = MemoryLedgerStore()
    store.write(LEDGER, data)
    records = LedgerRetroRecords(store)
    for read in (records.last, records.records, records.asked):
        with pytest.raises(OrgError, match=r"retros\.json"):
            read()
    records.append(record(1, "a"))
    assert [r.id for r in records.records()] == ["B1"] and records.asked() == frozenset({"a"})


def test_a_ledger_with_a_naive_time_reads_it_as_utc() -> None:
    store = MemoryLedgerStore()
    store.write(LEDGER, {"briefs": [{"id": "B1", "at": "2026-11-03T09:40:05", "since": None, "by": "cli", "items": [], "held_back": []}], "asked": []})
    back = LedgerRetroRecords(store).last()
    assert back is not None and back.at == ORIGIN.replace(day=3) and back.by == "cli"


def test_the_ledger_text_is_what_json_dumps(tmp_path: Path) -> None:
    harness = fs_ledger_store(tmp_path)
    LedgerRetroRecords(harness.store).append(record(1, "a"))
    text = OrgPaths(tmp_path).ledger_file(LEDGER).read_text(encoding="utf-8")
    assert json.loads(text)["briefs"][0]["id"] == "B1" and text.endswith("\n")
