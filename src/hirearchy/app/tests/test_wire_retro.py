"""``wire_retro``: the runtime has the ledger of the briefs held and the brief, built from the ports of the runtime - so a test that overrides a port runs the
brief over its own fake."""

from __future__ import annotations

from pathlib import Path

from hirearchy.app import fields_retro, wire_retro, wiring
from hirearchy.kernel import ROOT
from hirearchy.retro import RetroBriefs, RetroDue, RetroRecords
from hirearchy.retro._brief import FileRetroBriefs
from hirearchy.retro._due import FileRetroDue
from hirearchy.retro._ledger import LedgerRetroRecords
from hirearchy.retro.testing import MemoryRetroRecords
from hirearchy.telemetry import ProcessLabel
from hirearchy.telemetry._label import MutableProcessLabel


def test_the_runtime_has_the_ledger_and_the_brief(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.retro_records, LedgerRetroRecords) and isinstance(runtime.retro_records, RetroRecords)
    assert isinstance(runtime.retro_briefs, FileRetroBriefs) and isinstance(runtime.retro_briefs, RetroBriefs)
    assert isinstance(runtime.retro_due, FileRetroDue) and isinstance(runtime.retro_due, RetroDue)
    assert wire_retro.register in wiring.registrars() and fields_retro.STEP == "C-retro"


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.retro_records is not None and runtime.retro_briefs is not None
    assert list(tmp_path.iterdir()) == []


def test_each_port_is_built_once_per_organization(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.retro_briefs is runtime.retro_briefs and runtime.retro_records is runtime.retro_records


def test_the_brief_records_into_the_ledger_of_the_runtime(tmp_path: Path) -> None:
    ledger = MemoryRetroRecords()
    org = _org(tmp_path)
    runtime = wiring.open_runtime(org, {RetroRecords: ledger})
    brief = runtime.retro_briefs.brief()
    assert brief.id == "B1" and [r.id for r in ledger.records()] == ["B1"]
    assert not (org / ".runtime" / "retros.json").exists()


def test_the_brief_is_recorded_under_the_name_of_the_process(tmp_path: Path) -> None:
    org = _org(tmp_path)
    label = MutableProcessLabel()
    label.set("mcp")
    runtime = wiring.open_runtime(org, {ProcessLabel: label})
    runtime.retro_briefs.brief()
    (record,) = runtime.retro_records.records()
    assert record.by == "mcp" and (org / ".runtime" / "retros.json").is_file()


def _org(tmp_path: Path) -> Path:
    from hirearchy.app import Org

    org = Org.init(tmp_path / "org", "mission")
    org.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    return org.root


def test_the_trigger_reads_the_ledger_of_the_runtime(tmp_path: Path) -> None:
    ledger = MemoryRetroRecords()
    runtime = wiring.open_runtime(_org(tmp_path), {RetroRecords: ledger})
    assert runtime.retro_due.due() == "" and runtime.retro_due.due(listing=True) == ""  # an organization with no verdict has nothing due
