"""``FsCreationTimes`` and ``FsLedgerShape``: what the ladder reads of files that no other port shows."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from orgmcp.kernel import Message, OrgPaths
from orgmcp.stalls._ports import CreationTimes, FsCreationTimes, FsLedgerShape, LedgerShape

from ._support import RED


def task(created: str, path: Path | None = None) -> Message:
    return Message(sender="root", to="ceo", type="task", title="T", body="b", id="T-1", created=created, path=path)


# ------------------------------------------------------------------------------ creation times


def test_the_creation_times_are_a_port() -> None:
    assert isinstance(FsCreationTimes(), CreationTimes)


@RED
def test_a_task_was_created_when_its_stamp_says() -> None:
    stamp = datetime(2026, 10, 18, 10, 0, 7, tzinfo=timezone.utc)
    assert FsCreationTimes().of(task(stamp.isoformat(timespec="seconds"))) == stamp.timestamp()


@RED
def test_a_stamp_without_a_zone_is_local_time() -> None:
    naive = datetime(2026, 10, 18, 10, 0, 7)
    assert FsCreationTimes().of(task(naive.isoformat())) == naive.timestamp()


@RED
def test_a_stamp_that_does_not_read_gives_the_modification_time_of_the_file(tmp_path: Path) -> None:
    file = tmp_path / "T-1.md"
    file.write_text("x")
    os.utime(file, (1_700_000_000, 1_700_000_000))
    assert FsCreationTimes().of(task("not a date", file)) == 1_700_000_000.0
    assert FsCreationTimes().of(task("", file)) == 1_700_000_000.0


# ------------------------------------------------------------------------------ ledger shape


def test_the_ledger_shape_is_a_port(tmp_path: Path) -> None:
    assert isinstance(FsLedgerShape(OrgPaths(tmp_path)), LedgerShape)


@RED
def test_a_ledger_that_is_not_an_object_is_damaged(tmp_path: Path) -> None:
    (tmp_path / ".runtime").mkdir()
    shape = FsLedgerShape(OrgPaths(tmp_path))
    for text, damaged in [("{}", False), ('{"a": 1}', False), ("[]", True), ("42", True), ('"x"', True), ("null", True)]:
        (tmp_path / ".runtime" / "nudges.json").write_text(text)
        assert shape.damaged("nudges") is damaged, text


@RED
def test_a_ledger_that_is_missing_or_cannot_be_parsed_is_not_damaged_but_absent(tmp_path: Path) -> None:
    shape = FsLedgerShape(OrgPaths(tmp_path))
    assert shape.damaged("nudges") is False
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime" / "nudges.json").write_text("{ broken")
    assert shape.damaged("nudges") is False
