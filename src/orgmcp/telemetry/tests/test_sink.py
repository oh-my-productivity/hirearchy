# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from testkit import telemetry_world as telemetry
from testkit.legacy.orgmcp.core import ROOT, join_frontmatter, split_frontmatter

from orgmcp.kernel.testing import FakeClock
from orgmcp.telemetry._sink import FsEventSink


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    telemetry.reset()
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def read_events(org, kind=None):
    """Every event of the org, merged by time (the way a reader would)."""
    out = []
    for f in event_files(org):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))  # every line is a valid JSON object
    out.sort(key=lambda e: (e["ts"], e["seq"]))
    return [e for e in out if kind is None or e["kind"] == kind]


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


# --------------------------------------------------------------------------------------- writer: layout, envelope
def test_events_go_to_one_file_per_process_and_day_with_the_envelope(org):
    org.emit("custom.kind", trace="T1", thing=1)
    org.emit("custom.kind", thing=2)
    files = event_files(org)
    assert len(files) == 1
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert files[0].parent.name == today
    assert re.fullmatch(rf"cli-{os.getpid()}-\d{{13}}\.jsonl", files[0].name)
    first, second = read_events(org)
    assert [first["seq"], second["seq"]] == [1, 2]
    assert first["v"] == 1 and first["proc"] == "cli" and first["pid"] == os.getpid()
    assert first["kind"] == "custom.kind" and first["actor"] == "root" and first["run"] is None
    assert first["trace"] == "T1" and second["trace"] is None and first["thing"] == 1
    datetime.fromisoformat(first["ts"])  # ISO-8601 with an offset
    assert first["ts"].endswith("+00:00")


def test_actor_and_run_come_from_the_environment_of_the_process(org, monkeypatch):
    monkeypatch.setenv("ORG_AGENT", "ceo/eng")
    monkeypatch.setenv("ORG_RUN_ID", "ceo/eng@20260101T000000000000")
    org.emit("custom.kind")
    org.emit("custom.kind", actor="runtime", run="other@1")
    a, b = read_events(org)
    assert (a["actor"], a["run"]) == ("ceo/eng", "ceo/eng@20260101T000000000000")
    assert (b["actor"], b["run"]) == ("runtime", "other@1")


def test_the_process_name_is_in_the_file_name(org):
    telemetry.set_process("mcp")
    org.emit("custom.kind")
    org.emit("custom.kind", proc="scheduler")
    assert sorted(f.name.split("-")[0] for f in event_files(org)) == ["mcp", "scheduler"]
    assert {e["proc"] for e in read_events(org)} == {"mcp", "scheduler"}
    assert [e for e in read_events(org) if e["proc"] == "scheduler"][0]["actor"] == "runtime"


def sink_of(org, **injected):
    """``org`` emits through a sink of its runtime whose collaborators are replaced (the injected ports instead of module patch points)."""
    resources, runtime = org.runtime.resources, org.runtime
    parts = {"clock": runtime.clock, "retry_after": 5.0, **injected}
    sink = FsEventSink(runtime.paths, resources.event_pool, resources.event_pool, runtime.event_switch, resources.process_label,
                       parts["clock"], runtime.environment, runtime.ignore_list, parts["retry_after"])
    org.runtime = dataclasses.replace(runtime, events=sink)


def test_seq_restarts_in_the_next_days_file(org):
    clock = FakeClock(datetime.now(timezone.utc))
    sink_of(org, clock=clock)
    org.emit("custom.kind")
    org.emit("custom.kind")
    clock.advance(86400)
    org.emit("custom.kind")
    org.emit("custom.kind")
    days = sorted(f.parent.name for f in event_files(org))
    assert len(days) == 2 and days[0] != days[1]
    for f in event_files(org):
        assert [json.loads(l)["seq"] for l in f.read_text().splitlines()] == [1, 2]


def test_a_long_line_is_shrunk_to_8kb_and_marked(org):
    org.emit("custom.kind", text="x" * 50_000, items=[f"item-{i}" * 40 for i in range(500)], nested={"a": "y" * 20_000})
    (line,) = event_files(org)[0].read_text().splitlines()
    assert len(line.encode()) <= telemetry.LINE_MAX
    event = json.loads(line)
    assert event["truncated"] is True and event["kind"] == "custom.kind" and event["seq"] == 1
    assert event["text"].endswith("…")


def test_an_enormous_envelope_free_payload_still_fits(org):
    org.emit("custom.kind", **{f"field{i}": "z" * 3000 for i in range(40)})
    (line,) = event_files(org)[0].read_text().splitlines()
    assert len(line.encode()) <= telemetry.LINE_MAX
    assert json.loads(line)["truncated"] is True


def test_non_ascii_and_odd_values_are_written_as_valid_json(org):
    org.emit("custom.kind", text="héllo ✓ \ud800", path=Path("/x/y"), when=datetime(2026, 1, 1), n=float("inf"))
    (event,) = read_events(org)
    assert event["text"].startswith("héllo ✓") and event["path"] == "/x/y"


def test_clip_marks_a_cut():
    assert telemetry.clip("abc", 80) == "abc"
    cut = telemetry.clip("x" * 100, 80)
    assert len(cut) == 80 and cut.endswith("…")


# ------------------------------------------------------------------------------------------------ never raises
def test_events_false_disables_emission_entirely(org):
    configure(org, events=False)
    org.send(ROOT, "ceo", "hello")
    assert not (org.root / ".runtime" / "events").exists()
    configure(org, events=True)
    org.send(ROOT, "ceo", "hello again")
    assert [e["kind"] for e in read_events(org)] == ["msg.deliver"]


def test_nothing_is_written_where_there_is_no_organization(tmp_path):
    target = tmp_path / "nowhere" / "org"
    telemetry.emit(target, "custom.kind")
    assert not target.exists() and telemetry.dropped() == 0


def test_an_unwritable_event_dir_never_fails_the_operation(org, capsys):
    runtime = org.root / ".runtime"
    runtime.mkdir(exist_ok=True)
    (runtime / "events").write_text("a file where the directory should be")
    msg = org.send(ROOT, "ceo", "still delivered")
    assert (org.dir("ceo") / "inbox" / f"{msg.id}.md").is_file()
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.hire("ceo", "qa", "Tester", "Test.")
    assert org.exists("ceo/qa") and task.trace == task.id
    assert telemetry.dropped() >= 3
    err = capsys.readouterr().err
    assert err.count("event log is unavailable") == 1  # reported once per process, not per event


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_a_read_only_event_dir_never_fails_the_operation(org, capsys):
    org.emit("custom.kind")
    day = event_files(org)[0].parent
    telemetry.reset()  # a new process: its own file has to be created in the read-only day directory
    day.chmod(0o500)
    try:
        org.send(ROOT, "ceo", "still works")
        org.retire(ROOT, "ceo/eng", "bye")
    finally:
        day.chmod(0o700)
    assert not org.exists("ceo/eng") and telemetry.dropped() >= 2
    assert capsys.readouterr().err.count("event log is unavailable") == 1


def test_a_failing_serializer_and_circular_values_are_swallowed(org):
    loop: dict = {}
    loop["self"] = loop
    org.emit("custom.kind", loop=loop)

    class Bad:
        def __str__(self):
            raise RuntimeError("no string for you")

    org.emit("custom.kind", bad=Bad())
    org.emit("custom.kind", fine=1)
    assert telemetry.dropped() == 2
    assert [e.get("fine") for e in read_events(org)] == [1]


def test_the_log_recovers_when_the_directory_becomes_writable(org):
    runtime = org.root / ".runtime"
    runtime.mkdir(exist_ok=True)
    blocker = runtime / "events"
    blocker.write_text("x")
    sink_of(org, retry_after=0.0)
    org.emit("custom.kind")
    blocker.unlink()
    org.emit("custom.kind", after=True)
    (event,) = read_events(org)
    assert event["after"] is True and event["seq"] == 1


# ---------------------------------------------------------------------------------------- overhead, concurrency
def test_overhead_1000_events_take_well_under_a_second(org):
    org.emit("warmup")
    start = time.perf_counter()
    for i in range(1000):
        org.emit("bench", i=i, to="ceo", title="a title", chars=123)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"1000 events took {elapsed:.3f}s"
    assert len(read_events(org, "bench")) == 1000


WRITER = """
import sys
from pathlib import Path
from orgmcp.app import wiring
root, proc, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
wiring.process_resources().process_label.set(proc)
events = wiring.open_runtime(Path(root)).events
for i in range(n):
    events.emit("tool.call", tool="t", i=i, pad="p" * 200)
"""


def test_processes_writing_at_once_never_interleave(org):
    n = 400
    procs = [subprocess.Popen([sys.executable, "-c", WRITER, str(org.root), proc, str(n)]) for proc in ("mcp", "mcp", "scheduler")]
    for i in range(n):  # this process writes meanwhile
        org.emit("tool.call", tool="t", i=i, pad="p" * 200)
    for p in procs:
        assert p.wait(timeout=60) == 0
    files = event_files(org)
    assert len(files) == 4  # one per process
    total = 0
    for f in files:
        seqs = [json.loads(line)["seq"] for line in f.read_text().splitlines()]  # all lines parse
        assert seqs == list(range(1, n + 1)), f"{f.name}: lines lost or reordered"
        total += len(seqs)
    assert total == 4 * n
