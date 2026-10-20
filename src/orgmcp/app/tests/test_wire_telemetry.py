"""The telemetry ports in the runtime, and the process resources behind them. What the event files look like is what it was: ``tests/test_telemetry.py`` and the golden event shapes are the characterization."""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orgmcp.app import Org, wiring
from orgmcp.app._resources import ProcessResources
from orgmcp.eventlog import EVENTS_REL, PROCS
from orgmcp.kernel import Clock, EventSink, TraceTap
from orgmcp.kernel.testing import ListEventSink
from orgmcp.settings import EventSwitch
from orgmcp.settings.testing import MemoryOrgSettings
from orgmcp.snapshots import IgnoreList
from orgmcp.snapshots.testing import MemoryIgnoreList
from testkit.clocks import clock_ports
from orgmcp.telemetry import ArgumentSummarizer, EventRetention, EventSinks, ProcessLabel, TraceScope
from orgmcp.telemetry._label import MutableProcessLabel
from orgmcp.telemetry._pool import EventWriterPool
from orgmcp.telemetry._retention import FsEventRetention
from orgmcp.telemetry._sink import FsEventSink, FsEventSinks
from orgmcp.telemetry._summarize import JsonArgumentSummarizer
from orgmcp.telemetry._trace_scope import ThreadLocalTraceScope


def lines(root: Path) -> list[dict[str, object]]:
    return [json.loads(line) for f in sorted((root / EVENTS_REL).glob("*/*.jsonl")) for line in f.read_text(encoding="utf-8").splitlines()]


def files(root: Path) -> list[Path]:
    return sorted((root / EVENTS_REL).glob("*/*.jsonl"))


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    shutil.rmtree(made.root / EVENTS_REL, ignore_errors=True)  # the events of the construction are forgotten: a test sees only its own
    wiring.process_resources().reset()
    return made


# ------------------------------------------------------------------------------------------------------------ the runtime


def test_the_runtime_has_the_real_telemetry_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.events, FsEventSink) and isinstance(runtime.events, EventSink)
    assert isinstance(runtime.event_retention, FsEventRetention) and isinstance(runtime.event_retention, EventRetention)
    assert isinstance(runtime.argument_summarizer, JsonArgumentSummarizer) and isinstance(runtime.argument_summarizer, ArgumentSummarizer)
    assert isinstance(runtime.event_sinks, FsEventSinks) and isinstance(runtime.event_sinks, EventSinks)
    assert isinstance(runtime.process_label, MutableProcessLabel) and isinstance(runtime.process_label, ProcessLabel)
    assert isinstance(runtime.trace_scope, ThreadLocalTraceScope) and isinstance(runtime.trace_scope, TraceScope)
    assert isinstance(runtime.trace_tap, TraceTap)


def test_the_process_owns_the_pool_the_label_the_scope_and_the_sinks(tmp_path: Path) -> None:
    resources = wiring.process_resources()
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(resources.event_pool, EventWriterPool)
    assert runtime.process_label is resources.process_label and runtime.event_sinks is resources.event_sinks
    assert runtime.trace_scope is resources.trace_scope and runtime.trace_tap is resources.trace_scope


def test_two_runtimes_have_their_own_sink_over_the_same_pool(tmp_path: Path) -> None:
    one, two = wiring.open_runtime(tmp_path), wiring.open_runtime(tmp_path)
    assert one.events is not two.events and one.event_retention is not two.event_retention
    assert one.process_label is two.process_label and one.trace_scope is two.trace_scope


def test_the_sink_is_built_from_the_ports_of_its_runtime(tmp_path: Path) -> None:
    ignore, text = MemoryIgnoreList(), MemoryOrgSettings("---\nevents: true\n---\n")
    runtime = wiring.open_runtime(tmp_path, {IgnoreList: ignore, EventSwitch: _switch(text)})
    runtime.events.emit("custom.kind")
    assert ignore.text is not None and ".runtime/events/" in ignore.text.split()


def _switch(settings: MemoryOrgSettings) -> EventSwitch:
    from orgmcp.settings._switch import StampedEventSwitch

    return StampedEventSwitch(settings, settings)


def test_the_event_switch_of_the_runtime_decides(tmp_path: Path) -> None:
    off = MemoryOrgSettings("---\nevents: false\n---\n")
    wiring.open_runtime(tmp_path, {EventSwitch: _switch(off)}).events.emit("custom.kind")
    assert not (tmp_path / EVENTS_REL).exists()


def test_a_sink_override_replaces_the_port(tmp_path: Path) -> None:
    sink = ListEventSink()
    assert wiring.open_runtime(tmp_path, {EventSink: sink}).events is sink


def test_the_events_are_stamped_by_the_event_clock_of_the_runtime(org: Org) -> None:
    fixed = datetime(2031, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
    org.runtime = wiring.open_runtime(org.root, clock_ports(lambda: fixed, events=True))
    org.emit("custom.kind")
    assert lines(org.root)[0]["ts"] == "2031-05-06T07:08:09.000000+00:00"
    assert isinstance(org.runtime.clock, Clock)


def test_the_clock_of_the_runtime_does_not_stamp_the_events(org: Org) -> None:
    """A clock that a reading moves (the scenarios') must not be moved by the events: the stamps of the events are the clock of their own."""
    readings: list[int] = []

    def moving() -> datetime:
        readings.append(1)
        return datetime(2031, 5, 6, 7, 8, 9, tzinfo=timezone.utc)

    org.runtime = wiring.open_runtime(org.root, clock_ports(moving))
    org.emit("custom.kind")
    assert readings == [] and str(lines(org.root)[0]["ts"]).startswith(str(datetime.now(timezone.utc).year))


def test_the_event_clock_is_the_system_clock_of_a_plain_runtime(org: Org) -> None:
    runtime = wiring.open_runtime(org.root)
    before = datetime.now(timezone.utc)
    runtime.events.emit("custom.kind")
    ts = datetime.fromisoformat(str(lines(org.root)[0]["ts"]))
    assert before <= ts <= before + timedelta(seconds=5)


# ------------------------------------------------------------------------------------------------------------ the facade


def test_org_emit_goes_through_the_sink_of_its_runtime(org: Org) -> None:
    sink = ListEventSink()
    org.runtime = dataclasses.replace(org.runtime, events=sink)
    org.emit("custom.kind", actor="ceo", x=1)
    assert [(e.kind, e.actor, e.fields) for e in sink.events] == [("custom.kind", "ceo", {"x": 1})]


def test_org_emit_writes_the_event_and_reads_the_environment_when_it_emits(org: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORG_AGENT", "ceo/eng")
    monkeypatch.setenv("ORG_RUN_ID", "ceo/eng@1")
    org.emit("custom.kind", thing=1)
    (event,) = lines(org.root)
    assert (event["kind"], event["actor"], event["run"], event["thing"], event["pid"]) == ("custom.kind", "ceo/eng", "ceo/eng@1", 1, os.getpid())


def test_org_emit_never_raises(org: Org) -> None:
    class Boom:
        def __str__(self) -> str:
            raise RuntimeError("x")

    org.emit("custom.kind", boom=Boom())
    assert wiring.process_resources().event_pool.dropped() == 1


def test_the_process_label_is_global_so_org_code_in_the_scheduler_says_scheduler(org: Org) -> None:
    wiring.process_resources().process_label.set("scheduler")
    org.emit("custom.kind")
    (event,) = lines(org.root)
    assert (event["proc"], event["actor"]) == ("scheduler", "runtime") and files(org.root)[0].name.startswith("scheduler-")


def test_one_file_per_process_and_day_across_several_runtimes_of_the_same_root(org: Org) -> None:
    other = Org(org.root)
    org.emit("a")
    other.emit("b")
    wiring.open_runtime(org.root).events.emit("c")
    wiring.open_runtime(org.root).events.emit("d")
    assert len(files(org.root)) == 1
    assert [(e["kind"], e["seq"]) for e in lines(org.root)] == [("a", 1), ("b", 2), ("c", 3), ("d", 4)]


def test_a_second_process_writes_its_own_file(org: Org) -> None:
    org.emit("mine")
    code = "from pathlib import Path; import sys; from orgmcp.app import wiring; wiring.process_resources().process_label.set('mcp'); wiring.open_runtime(Path(sys.argv[1])).events.emit('theirs')"
    subprocess.run([sys.executable, "-c", code, str(org.root)], check=True, timeout=60)
    assert sorted(f.name.split("-")[0] for f in files(org.root)) == ["cli", "mcp"]


# ----------------------------------------------------------------------------------------------- the process resources


def test_reset_closes_the_files_and_forgets_the_counters_the_label_and_the_sinks(org: Org) -> None:
    resources = wiring.process_resources()
    org.emit("custom.kind")
    wiring.process_resources().process_label.set("mcp")
    resources.event_pool.drop("x")
    cached = resources.event_sinks.for_root(org.root)
    resources.reset()
    assert resources.event_pool.dropped() == 0 and resources.process_label.get() == "cli"
    assert resources.event_sinks.for_root(org.root) is not cached


def test_reset_keeps_the_objects_of_the_resources() -> None:
    resources = wiring.process_resources()
    before = (resources.event_pool, resources.process_label, resources.trace_scope, resources.event_sinks, resources.message_parser)
    resources.reset()
    assert before == (resources.event_pool, resources.process_label, resources.trace_scope, resources.event_sinks, resources.message_parser)


def test_the_resources_can_be_made_without_arguments_for_the_telemetry_part() -> None:
    from orgmcp.mail._parser import CachingMessageParser

    resources = ProcessResources(CachingMessageParser())
    assert isinstance(resources.event_pool, EventWriterPool) and isinstance(resources.event_sinks, FsEventSinks)
    assert resources.process_label.get() == "cli" and isinstance(resources.trace_scope, ThreadLocalTraceScope)


def test_the_sinks_of_a_custom_set_of_resources_use_that_set(tmp_path: Path) -> None:
    from orgmcp.mail._parser import CachingMessageParser

    (tmp_path / "ORG.md").write_text("---\nevents: true\n---\n", encoding="utf-8")
    resources = ProcessResources(CachingMessageParser())
    resources.event_sinks.for_root(tmp_path).emit("custom.kind")
    assert len(files(tmp_path)) == 1 and wiring.process_resources().event_pool is not resources.event_pool


# ------------------------------------------------------------------------------------------- the ports, called by root


def test_emit_by_root_writes_the_event_with_the_old_arguments(org: Org) -> None:
    wiring.open_runtime(org.root).events.emit("tool.call", proc="mcp", actor="ceo", trace="T", tool="status", ok=True)
    (event,) = lines(org.root)
    assert (event["proc"], event["actor"], event["trace"], event["tool"]) == ("mcp", "ceo", "T", "status")


def test_emit_by_root_accepts_a_string_and_never_raises(org: Org, tmp_path: Path) -> None:
    wiring.open_runtime(Path(str(org.root))).events.emit("custom.kind")
    wiring.open_runtime(tmp_path / "nowhere").events.emit("custom.kind")
    assert len(lines(org.root)) == 1 and not (tmp_path / "nowhere").exists() and wiring.process_resources().event_pool.dropped() == 0


def test_the_process_name_functions(org: Org) -> None:
    assert wiring.process_resources().process_label.get() == "cli"
    wiring.process_resources().process_label.set("mcp")
    assert wiring.process_resources().process_label.get() == "mcp" == wiring.process_resources().process_label.get()
    wiring.process_resources().process_label.set("nonsense")
    assert wiring.process_resources().process_label.get() == "cli"
    assert set(PROCS) == {"scheduler", "mcp", "cli"}


def test_reset_is_the_reset_of_the_resources(org: Org) -> None:
    wiring.process_resources().process_label.set("mcp")
    org.emit("custom.kind")
    wiring.process_resources().reset()
    assert wiring.process_resources().process_label.get() == "cli" and wiring.process_resources().event_pool.dropped() == 0


def test_traces_seen_and_note_trace_are_the_scope_and_the_tap_of_the_runtime(org: Org) -> None:
    with wiring.process_resources().trace_scope.collect() as seen:
        org.runtime.trace_tap.note("a")
        wiring.process_resources().trace_scope.note("b")
        with org.runtime.trace_scope.collect() as inner:
            wiring.process_resources().trace_scope.note("c")
    assert seen == ["a", "b"] and inner == ["c"]


def test_a_delivery_notes_its_trace_for_the_tool_call(org: Org) -> None:
    org.hire("root", "ceo", "Chief", "Run.", can_hire=True)
    with wiring.process_resources().trace_scope.collect() as seen:
        task = org.delegate("root", "ceo", "T", "g", "a", budget=3)
    assert seen == [task.id]


def test_prune_removes_through_the_retention_of_the_runtime(org: Org) -> None:
    base = org.root / EVENTS_REL
    old = base / (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    old.mkdir(parents=True)
    (old / "mcp-1-1.jsonl").write_text("{}\n")
    assert wiring.open_runtime(org.root).event_retention.prune(30) == [old.name] and not old.exists()
    assert wiring.open_runtime(org.root / "missing").event_retention.prune(30) == []


def test_summarize_args_is_the_summarizer(org: Org) -> None:
    assert org.runtime.argument_summarizer.summarize({"to": "ceo", "body": "abc", "x": None}) == {"to": "ceo", "body_chars": 3}


def test_ensure_ignored_writes_the_lines_through_the_ignore_list_and_never_raises(org: Org, tmp_path: Path) -> None:
    (org.root / ".gitignore").write_text(".tmp-*\n", encoding="utf-8")
    wiring.open_runtime(org.root).ignore_list.ensure_runtime_files()
    assert ".runtime/events/" in (org.root / ".gitignore").read_text(encoding="utf-8").split()
    wiring.open_runtime(tmp_path / "nowhere").ignore_list.ensure_runtime_files()
    assert not (tmp_path / "nowhere").exists()


def test_emission_stays_cheap(org: Org) -> None:
    org.emit("warmup")
    start = time.perf_counter()
    for i in range(2000):
        org.emit("bench", i=i, to="ceo", title="a title", chars=123)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.5, f"2000 events took {elapsed:.3f}s ({elapsed / 2000 * 1e6:.0f} us each)"
    assert len(lines(org.root)) == 2001
