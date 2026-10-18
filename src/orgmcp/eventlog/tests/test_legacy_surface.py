"""The legacy modules that still exist agree with the package: the constants are the same objects, and the lines the legacy writer
(``telemetry``) puts on the disk are what the package reads (the golden event shape: the file format does not change)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orgmcp.eventlog import DAY_RE, ENVELOPE, EVENTS_REL, LINE_MAX, PROCS, SCHEMA_VERSION, event_file
from orgmcp.eventlog._reader import FsEventReader
from orgmcp.kernel import OrgPaths

from ._legacy import legacy


@pytest.mark.xfail(strict=True, reason="red: A-eventlog")
def test_the_writer_takes_the_format_constants_from_the_package() -> None:
    telemetry = legacy("telemetry")
    assert telemetry.SCHEMA_VERSION == SCHEMA_VERSION and telemetry.LINE_MAX == LINE_MAX
    assert telemetry.EVENTS_REL == EVENTS_REL and telemetry.ENVELOPE == ENVELOPE and telemetry.PROCS == PROCS
    assert telemetry.DAY_RE is DAY_RE and telemetry.ENVELOPE is ENVELOPE


def test_the_query_module_keeps_its_old_names_for_the_constants() -> None:
    observe = legacy("observe")
    assert observe.EVENTS_DIR == EVENTS_REL and observe.ENVELOPE == set(ENVELOPE)


@pytest.mark.xfail(strict=True, reason="red: A-eventlog")
def test_what_the_writer_writes_the_reader_reads(tmp_path: Path) -> None:
    core, telemetry = legacy("core"), legacy("telemetry")
    org = core.Org.init(tmp_path / "org", "Mission", {"events": True})
    try:
        telemetry.emit(org.root, "tool.call", actor="root", proc="mcp", tool="status", ok=True, ms=3)
    finally:
        telemetry.reset()
    reader = FsEventReader(OrgPaths(org.root))
    files = [f for f in reader.files() if f.proc == "mcp"]
    assert files and DAY_RE.fullmatch(files[0].day) and files[0].proc in PROCS
    raw = json.loads(files[0].path.read_text().splitlines()[0])
    assert tuple(raw)[: len(ENVELOPE)] == ENVELOPE and raw["v"] == SCHEMA_VERSION
    assert [ev["kind"] for ev in reader.events() if ev["kind"] == "tool.call"] == ["tool.call"]
    assert event_file(files[0].path) == files[0]
