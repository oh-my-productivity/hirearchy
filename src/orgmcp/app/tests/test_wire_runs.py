"""``wire_runs``: the runtime has the run ports, built from the kernel's ports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import orgmcp.core as core
from orgmcp.app import wiring
from orgmcp.runs import RunLogReader, RunLogWriter, RunRegistry
from orgmcp.runs._reader import FsRunLogReader
from orgmcp.runs._registry import FsRunRegistry
from orgmcp.runs._writer import FsRunLogWriter
from orgmcp.runs.testing import MemoryRuns


def test_the_runtime_has_the_run_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.run_log_writer, FsRunLogWriter) and isinstance(runtime.run_log_writer, RunLogWriter)
    assert isinstance(runtime.run_log_reader, FsRunLogReader) and isinstance(runtime.run_log_reader, RunLogReader)
    assert isinstance(runtime.run_registry, FsRunRegistry) and isinstance(runtime.run_registry, RunRegistry)


def test_building_the_run_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.run_log_reader.count("ceo") == 0 and runtime.run_registry.all() == {}
    assert list(tmp_path.iterdir()) == []


def test_logs_are_stamped_by_the_clock_of_the_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``core.utcnow`` is a patch point of the tests until they are converted: the clock of the runtime reads it at the time of the call."""
    (tmp_path / "ceo").mkdir()
    monkeypatch.setattr(core, "utcnow", lambda: datetime(2031, 5, 6, 7, 8, 9, 123456, tzinfo=timezone.utc))
    assert wiring.open_runtime(tmp_path).run_log_writer.create("ceo") == tmp_path / "ceo" / "runs" / "20310506T070809123456.log"


def test_the_registry_is_the_running_ledger_of_the_runtime(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    runtime.run_registry.record("ceo", {"pgid": 7})
    assert json.loads((tmp_path / ".runtime" / "running.json").read_text(encoding="utf-8")) == {"ceo": {"pgid": 7}}
    assert runtime.ledgers.read("running") == {"ceo": {"pgid": 7}}


def test_the_registry_is_written_through_the_atomic_writer_of_the_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[tuple[Path, str]] = []
    monkeypatch.setattr(core, "atomic_write", lambda path, text: written.append((path, text)))
    wiring.open_runtime(tmp_path).run_registry.record("ceo", {"pgid": 7})
    assert written == [(tmp_path / ".runtime" / "running.json", json.dumps({"ceo": {"pgid": 7}}, indent=2) + "\n")]


def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    fake = MemoryRuns(root=tmp_path)
    runtime = wiring.open_runtime(tmp_path, {RunLogReader: fake})
    assert runtime.run_log_reader is fake
    assert runtime.run_log_writer is not fake and runtime.run_registry is not fake  # other ports, still the files


def test_every_runtime_has_its_own_run_ports(tmp_path: Path) -> None:
    first, second = wiring.open_runtime(tmp_path), wiring.open_runtime(tmp_path)
    assert first.run_log_writer is not second.run_log_writer and first.run_registry is not second.run_registry
