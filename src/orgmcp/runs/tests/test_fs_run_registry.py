"""``FsRunRegistry``: the file ``.runtime/running.json`` is what it always was."""

from __future__ import annotations

import json
from pathlib import Path

from orgmcp.kernel import JsonObject, OrgPaths
from orgmcp.kernel.testing import MemoryLedgerStore, fs_ledger_store
from orgmcp.runs import RunRegistry
from orgmcp.runs._registry import FsRunRegistry

from ._red import red

pytestmark = red

RECORD: JsonObject = {"pgid": 5, "lstart": "Sun Oct 18 10:00:00 2026", "started": 1.5, "scheduler": 9, "log": "ceo/runs/x.log"}


def test_the_registry_is_the_running_ledger(tmp_path: Path) -> None:
    registry = FsRunRegistry(fs_ledger_store(tmp_path).store)
    assert isinstance(registry, RunRegistry)
    registry.record("ceo", RECORD)
    registry.record("ceo/eng", {**RECORD, "pgid": 6})
    text = (tmp_path / ".runtime" / "running.json").read_text(encoding="utf-8")
    assert text == json.dumps({"ceo": RECORD, "ceo/eng": {**RECORD, "pgid": 6}}, indent=2) + "\n"


def test_the_ledger_is_named_running(tmp_path: Path) -> None:
    store = MemoryLedgerStore()
    FsRunRegistry(store).record("ceo", RECORD)
    assert list(store.texts) == ["running"] and store.read("running") == {"ceo": RECORD}


def test_forgetting_nobody_writes_nothing(tmp_path: Path) -> None:
    registry = FsRunRegistry(fs_ledger_store(tmp_path).store)
    registry.forget("ceo")
    assert not (tmp_path / ".runtime").exists()
    registry.record("ceo", RECORD)
    before = (tmp_path / ".runtime" / "running.json").stat().st_mtime_ns
    registry.forget("nobody")
    assert (tmp_path / ".runtime" / "running.json").stat().st_mtime_ns == before


def test_forgetting_the_last_run_leaves_an_empty_ledger(tmp_path: Path) -> None:
    registry = FsRunRegistry(fs_ledger_store(tmp_path).store)
    registry.record("ceo", RECORD)
    registry.forget("ceo")
    assert (tmp_path / ".runtime" / "running.json").read_text(encoding="utf-8") == "{}\n"


def test_replacing_writes_the_records_as_they_are(tmp_path: Path) -> None:
    registry = FsRunRegistry(fs_ledger_store(tmp_path).store)
    registry.replace({"a": RECORD})
    assert json.loads((OrgPaths(tmp_path).ledger_file("running")).read_text(encoding="utf-8")) == {"a": RECORD}


def test_a_ledger_written_by_the_legacy_code_is_read(tmp_path: Path) -> None:
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime" / "running.json").write_text(json.dumps({"ceo": RECORD, "x": "junk"}, indent=2) + "\n", encoding="utf-8")
    assert FsRunRegistry(fs_ledger_store(tmp_path).store).all() == {"ceo": RECORD}
