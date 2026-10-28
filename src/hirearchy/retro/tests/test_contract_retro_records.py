"""Contract of ``RetroRecords``: the briefs held, oldest first, at most 50, and every item key ever offered, at most 1000. The ledger over a file and the
fake keep the same records."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.retro import ASKED_KEPT, RECORDS_KEPT, RetroRecords
from hirearchy.retro.testing import IMPLEMENTATIONS

from ._records import record


@pytest.fixture(params=IMPLEMENTATIONS[RetroRecords], ids=lambda factory: factory.__name__)
def records(request: pytest.FixtureRequest, tmp_path: Path) -> RetroRecords:
    made = request.param(tmp_path)
    assert isinstance(made, RetroRecords)
    return made


def test_an_organization_that_held_no_brief_has_no_record_and_has_asked_nothing(records: RetroRecords) -> None:
    assert records.last() is None
    assert records.records() == ()
    assert records.asked() == frozenset()


def test_append_then_last_and_records_oldest_first(records: RetroRecords) -> None:
    records.append(record(1, "a"))
    records.append(record(2, "b"))
    assert records.last() == record(2, "b")
    assert records.records() == (record(1, "a"), record(2, "b"))


def test_a_record_reads_back_as_it_was_written(records: RetroRecords) -> None:
    first = record(1, "service|lead|C1", "checker-add|memos|C4", lapsed=1)
    records.append(first)
    back = records.last()
    assert back == first
    assert back is not None and back.since is None and back.at.tzinfo is not None
    assert back.items[0].effect == {"service": "lead/service|lead|C1"} and back.held_back == ("held|1",)


def test_records_keep_the_newest_50(records: RetroRecords) -> None:
    for n in range(1, RECORDS_KEPT + 6):
        records.append(record(n))
    kept = records.records()
    assert len(kept) == RECORDS_KEPT
    assert kept[0].id == "B6" and kept[-1].id == f"B{RECORDS_KEPT + 5}" and records.last() == kept[-1]


def test_asked_keeps_every_key_once(records: RetroRecords) -> None:
    records.append(record(1, "a", "b"))
    records.append(record(2, "b", "c"))
    assert records.asked() == frozenset({"a", "b", "c"})


def test_asked_keeps_at_most_1000_and_drops_the_oldest_keys_first(records: RetroRecords) -> None:
    keys = [f"k{i:04d}" for i in range(ASKED_KEPT + 30)]
    for start in range(0, len(keys), 3):
        records.append(record(start // 3 + 1, *keys[start:start + 3]))
    asked = records.asked()
    assert len(asked) == ASKED_KEPT
    assert "k0000" not in asked and "k0029" not in asked and "k0030" in asked and keys[-1] in asked


def test_a_key_asked_again_moves_to_the_newest_end(records: RetroRecords) -> None:
    records.append(record(1, "old"))
    for n in range(2, 335):
        records.append(record(n, f"x{n}a", f"x{n}b", f"x{n}c"))
    assert len(records.asked()) == ASKED_KEPT  # "old" and 999 others
    records.append(record(335, "old"))  # offered again: it is now the newest
    for n in (336, 337):
        records.append(record(n, f"y{n}a", f"y{n}b", f"y{n}c"))
    asked = records.asked()
    assert "old" in asked and len(asked) == ASKED_KEPT
    assert "x2a" not in asked and "x3c" not in asked and "x4a" in asked  # the six oldest went, "old" stayed
