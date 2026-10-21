"""The writer and the reader agree: the lines the writer (``telemetry``) puts on the disk are what the package reads (the golden
event shape: the file format does not change)."""

from __future__ import annotations

import json
from pathlib import Path

from hirearchy.eventlog import DAY_RE, ENVELOPE, PROCS, SCHEMA_VERSION, event_file
from hirearchy.eventlog._reader import FsEventReader
from hirearchy.kernel import OrgPaths

from ._reach import reach


def test_what_the_writer_writes_the_reader_reads(tmp_path: Path) -> None:
    core, wiring = reach("core"), reach("app.wiring")
    org = core.Org.init(tmp_path / "org", "Mission", {"events": True})
    try:
        wiring.open_runtime(org.root).events.emit("tool.call", actor="root", proc="mcp", tool="status", ok=True, ms=3)
    finally:
        wiring.process_resources().reset()
    reader = FsEventReader(OrgPaths(org.root))
    files = [f for f in reader.files() if f.proc == "mcp"]
    assert files and DAY_RE.fullmatch(files[0].day) and files[0].proc in PROCS
    raw = json.loads(files[0].path.read_text().splitlines()[0])
    assert tuple(raw)[: len(ENVELOPE)] == ENVELOPE and raw["v"] == SCHEMA_VERSION
    assert [ev["kind"] for ev in reader.events() if ev["kind"] == "tool.call"] == ["tool.call"]
    assert event_file(files[0].path) == files[0]
