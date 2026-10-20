"""The event log (emission side): files, envelope, safety, retention, trace stamping and every emitted kind."""

import dataclasses
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import testkit

from orgmcp import telemetry
from orgmcp.cli import main
from orgmcp.core import ROOT, Message, Org, join_frontmatter, split_frontmatter
from orgmcp.kernel.testing import FakeClock
from orgmcp.eligibility import FailureCounter
from orgmcp.eligibility.testing import MemoryFailureCounter
from orgmcp.scheduler import Scheduler, ignore_runtime_files
from orgmcp.scheduler.testing import ScriptedLadder
from orgmcp.stalls import StallLadder
from orgmcp.telemetry._sink import FsEventSink

FAKE = str(testkit.FAKE_AGENT)
SILENT = {"echo": lambda _: None}


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


def fake_runner(mode="work"):
    def build(org, addr, prompt):
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}
        return [sys.executable, FAKE], org.dir(addr), env

    return build


def drain(sched, limit=60.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.02)
    assert time.time() < deadline, "organization never went idle"


def run_all(org, mode="work", **kw):
    sched = Scheduler(org, fake_runner(mode), **SILENT, **kw)
    sched.acquire()
    try:
        drain(sched)
    finally:
        sched.release()
    return sched


class Clock:
    def __init__(self):
        self.offset = 0.0

    def __call__(self):
        return time.time() + self.offset

    def advance(self, seconds):
        self.offset += seconds


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


def test_a_message_delivery_with_events_is_not_noticeably_slower(org):
    def timed(n=60):
        start = time.perf_counter()
        for _ in range(n):
            org.send(ROOT, "ceo", "x")
        return time.perf_counter() - start

    configure(org, events=False)
    off = timed()
    configure(org, events=True)
    on = timed()
    assert on < off * 3 + 0.5


WRITER = """
import sys
from orgmcp import telemetry
root, proc, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
telemetry.set_process(proc)
for i in range(n):
    telemetry.emit(root, "tool.call", tool="t", i=i, pad="p" * 200)
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


# --------------------------------------------------------------------------------- retention and git hygiene
def test_prune_removes_only_old_day_directories(org):
    base = org.root / ".runtime" / "events"
    today = datetime(2026, 10, 18, tzinfo=timezone.utc)
    for offset in (0, 1, 29, 30, 31, 90):
        d = base / (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        d.mkdir(parents=True)
        (d / "mcp-1-1.jsonl").write_text("{}\n")
    (base / "notes").mkdir()
    removed = telemetry.prune(org.root, 30, today=today)
    assert removed == ["2026-07-20", "2026-09-17"]
    assert sorted(p.name for p in base.iterdir()) == ["2026-09-18", "2026-09-19", "2026-10-17", "2026-10-18", "notes"]
    assert telemetry.prune(org.root, 30, today=today) == []
    assert telemetry.prune(org.root / "missing", 30) == []


def test_the_scheduler_prunes_once_a_day_and_says_so(org):
    base = org.root / ".runtime" / "events"
    old = base / (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    old.mkdir(parents=True)
    (old / "mcp-1-1.jsonl").write_text("{}\n")
    clock = Clock()
    sched = Scheduler(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.tick()
    assert not old.exists()
    (prune,) = read_events(org, "prune")
    assert prune["removed_days"] == [old.name] and prune["proc"] == "scheduler" and prune["actor"] == "runtime"
    again = base / (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    again.mkdir()
    sched.tick()
    assert again.exists()  # not within a day
    clock.advance(86400 + 1)
    sched.tick()
    assert not again.exists()


def test_keep_days_is_configurable(org):
    configure(org, events_keep_days=3)
    base = org.root / ".runtime" / "events"
    old = base / (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    old.mkdir(parents=True)
    Scheduler(org, fake_runner("idle"), **SILENT).tick()
    assert not old.exists()


def test_new_orgs_ignore_the_events_in_git(tmp_path):
    org = Org.init(tmp_path / "fresh", "m")
    assert ".runtime/events/" in (org.root / ".gitignore").read_text().split()
    org.hire(ROOT, "ceo", "CEO", "c", can_hire=True)
    org.send(ROOT, "ceo", "hi")
    org.commit("after events")
    tracked = subprocess.run(["git", "ls-files"], cwd=org.root, capture_output=True, text=True).stdout
    assert event_files(org) and ".runtime/events" not in tracked


def test_existing_orgs_get_the_ignore_line_from_the_scheduler_and_from_the_first_event(tmp_path):
    org = Org.init(tmp_path / "old", "m")
    (org.root / ".gitignore").write_text(".tmp-*\nruns/\n.kiro/\n.runtime/scheduler.pid\n")
    ignore_runtime_files(org.root)
    assert ".runtime/events/" in (org.root / ".gitignore").read_text().split()
    (org.root / ".gitignore").write_text(".tmp-*\nruns/\n")
    org.emit("custom.kind")  # the first event of an org that predates the event log
    assert ".runtime/events/" in (org.root / ".gitignore").read_text().split()


def test_new_config_keys_have_defaults(org):
    cfg = org.config
    assert cfg["events"] is True and cfg["events_keep_days"] == 30 and cfg["heartbeat_seconds"] == 60


# ---------------------------------------------------------------------------------------------- trace stamping
def frontmatter(org, addr, box, msg):
    return split_frontmatter((org.dir(addr) / box / f"{msg.id}.md").read_text())[0]


def deliveries(org):
    return {e["id"]: e for e in read_events(org, "msg.deliver")}


def test_rule_new_a_root_task_is_its_own_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    assert task.trace == task.id
    assert frontmatter(org, "ceo", "inbox", task)["trace"] == task.id
    assert frontmatter(org, ROOT, "sent", task)["trace"] == task.id
    ev = deliveries(org)[task.id]
    assert ev["trace"] == task.id and ev["trace_rule"] == "new" and ev["type"] == "task" and ev["from"] == "root"
    assert ev["to"] == "ceo" and ev["budget"] == 5 and ev["chars"] > 0 and ev["wake"] is True and "body" not in ev


def test_rule_link_a_result_follows_its_task(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    result = org.report("ceo", task.id, "done", "ok")
    assert result.trace == task.id
    ev = deliveries(org)[result.id]
    assert ev["trace"] == task.id and ev["trace_rule"] == "link" and ev["reply_to"] == task.id and ev["status"] == "done"


def test_rule_link_via_reply_to_on_a_plain_note(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    note = org.send("ceo", ROOT, "a question", reply_to=task.id)
    assert note.trace == task.id and deliveries(org)[note.id]["trace_rule"] == "link"


def test_rule_link_via_revises_keeps_the_trace_of_the_revised_task(org):
    first = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    org.report("ceo", first.id, "done", "ok")
    redo = org.delegate(ROOT, "ceo", "T again", "g", "a", budget=9, revises=first.id)
    assert redo.trace == first.id and redo.id != first.id
    assert deliveries(org)[redo.id]["trace_rule"] == "link" and deliveries(org)[redo.id]["revises"] == first.id
    # and a manager's own rework of its delegation stays in the same trace
    org.begin_run("ceo")
    sub = org.delegate("ceo", "ceo/eng", "Sub", "g", "a", budget=2)
    redo_sub = org.delegate("ceo", "ceo/eng", "Sub again", "g", "a", budget=2, revises=sub.id)
    assert sub.trace == first.id and redo_sub.trace == first.id


def test_rule_open_task_a_manager_stamps_what_it_sends_with_its_open_tasks_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    sub = org.delegate("ceo", "ceo/eng", "Sub", "g", "a", budget=3)  # no batch needed: the open task decides
    assert sub.trace == task.id and deliveries(org)[sub.id]["trace_rule"] == "open-task"
    note = org.send("ceo", "ceo/eng", "psst")
    grant = org.send("ceo", "ceo/eng", "more runs", budget=1)
    assert note.trace == grant.trace == task.id


def test_rule_batch_picks_the_one_trace_of_the_current_batch(org):
    a = org.delegate(ROOT, "ceo", "A", "g", "a", budget=8)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    b = org.delegate(ROOT, "ceo", "B", "g", "a", budget=8)
    org.begin_run("ceo")  # inflight: only B; open tasks: A and B (two traces)
    note = org.send("ceo", "ceo/eng", "about B")
    assert note.trace == b.id != a.id
    assert deliveries(org)[note.id]["trace_rule"] == "batch"


def test_rule_ambiguous_leaves_the_trace_empty_and_lists_candidates(org):
    a = org.delegate(ROOT, "ceo", "A", "g", "a", budget=8)
    b = org.delegate(ROOT, "ceo", "B", "g", "a", budget=8)
    org.begin_run("ceo")  # inflight holds both
    note = org.send("ceo", "ceo/eng", "about both")
    assert note.trace is None and "trace" not in frontmatter(org, "ceo", "sent", note)
    ev = deliveries(org)[note.id]
    assert ev["trace"] is None and ev["trace_rule"] == "ambiguous"
    assert ev["trace_candidates"] == sorted([a.id, b.id])


def test_root_notes_without_a_link_are_ambiguous_and_sender_without_context_too(org):
    note = org.send(ROOT, "ceo", "hello")
    assert note.trace is None and deliveries(org)[note.id]["trace_rule"] == "ambiguous"


def test_the_trace_follows_the_whole_chain_down_and_up(org):
    root_task = org.delegate(ROOT, "ceo", "Ship", "g", "a", budget=8)
    org.begin_run("ceo")
    sub = org.delegate("ceo", "ceo/eng", "Build", "g", "a", budget=3)
    org.begin_run("ceo/eng")
    up = org.report("ceo/eng", sub.id, "done", "built")
    org.end_run("ceo/eng", ok=True)
    org.end_run("ceo", ok=True)
    org.begin_run("ceo")
    top = org.report("ceo", root_task.id, "done", "shipped")
    assert {m.trace for m in (root_task, sub, up, top)} == {root_task.id}


def test_runtime_notices_carry_the_trace_of_the_task_when_given(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    notice = org.notify("ceo", "reminder", "do it", trace=task.id)
    assert notice.trace == task.id and deliveries(org)[notice.id]["trace_rule"] == "given"
    plain = org.notify("ceo", "plain", "no task")
    assert plain.trace is None and deliveries(org)[plain.id]["from"] == "runtime"


def test_stall_notices_and_nudge_events_carry_the_task_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    clock = Clock()
    sched = Scheduler(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.acquire()
    try:
        drain(sched)
        for _ in range(3):
            clock.advance(float(org.config["stall_after"]) + 1)
            drain(sched)
    finally:
        sched.release()
    notices = [m for m in org.received("ceo") + org.received(ROOT) if m.sender == "runtime" and m.title.endswith(": T")]
    assert len(notices) == 2 and {m.trace for m in notices} == {task.id}
    nudges = read_events(org, "stall.nudge")
    assert [(n["task"], n["to"], n["step"], n["trace"]) for n in nudges] == [
        (task.id, "ceo", 0, task.id), (task.id, "root", 1, task.id)]


def test_old_messages_without_a_trace_still_load_and_work(org):
    old = org.dir("ceo") / "inbox" / "20200101T000000000000-root-aaaa.md"
    old.write_text("---\nid: 20200101T000000000000-root-aaaa\nfrom: root\nto: ceo\ntype: task\ntitle: Old\n"
                   "created: '2020-01-01T00:00:00+00:00'\nhops: 0\nbudget: 4\n---\nbody\n")
    m = Message.load(old)
    assert m.trace is None and m.title == "Old"
    # an agent with only unstamped context sends without a trace and nothing breaks
    note = org.send("ceo", ROOT, "status?")
    assert note.trace is None
    result = org.report("ceo", m.id, "done", "ok")  # reply to an unstamped task: no link, falls through, no crash
    assert result.trace is None and deliveries(org)[result.id]["trace_rule"] == "ambiguous"


def test_the_trace_is_in_the_file_but_not_in_what_agents_are_shown(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    shown = task.render()
    assert task.id in shown and "trace" not in shown.lower().replace(task.id, "")
    text = (org.dir("ceo") / "inbox" / f"{task.id}.md").read_text()
    assert f"trace: {task.id}" in text
    assert "trace" not in org.run_prompt("ceo", [task]).replace(task.id, "").lower().split("# new messages")[1]


def test_trace_of_ignores_ids_that_are_paths(org):
    assert org.trace_of("ceo", "../../ORG") is None and org.trace_of("ceo", "") is None and org.trace_of("ceo", None) is None


# --------------------------------------------------------------------------- org operations: hire, pause, ...
def test_hire_retire_pause_resume_events(org):
    org.hire("ceo", "qa", "Tester", "Test things.", model="m1")
    (hire,) = [e for e in read_events(org, "agent.hire") if e["agent"] == "ceo/qa"]
    assert hire["by"] == "ceo" and hire["actor"] == "ceo" and hire["role"] == "Tester"
    assert hire["model"] == "m1" and hire["tools"] == []
    org.pause("ceo/qa", "failures")
    org.resume("ceo/qa", "manual")
    pause, resume = read_events(org, "agent.pause")[-1], read_events(org, "agent.resume")[-1]
    assert pause["agent"] == "ceo/qa" and pause["reason"] == "failures"
    assert resume["agent"] == "ceo/qa" and resume["reason"] == "manual" and resume["previous"] == "failures"
    org.resume("ceo/qa")  # not paused: nothing to record
    assert len(read_events(org, "agent.resume")) == 1
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.retire(ROOT, "ceo/eng", "no longer needed")
    (ret,) = read_events(org, "agent.retire")
    assert ret["agent"] == "ceo/eng" and ret["by"] == "root" and ret["reason"] == "no longer needed"
    assert ret["returned_budget"] == 0


def test_service_events(org):
    brief = dict(description="A brief.", acceptance=["Short"], deliverable={"description": "one file"}, budget=4)
    org.define_service(ROOT, "ceo", "weekly", **brief)
    org.define_service(ROOT, "ceo", "weekly", add_acceptance=["Sourced"])
    org.revise_playbook("ceo", "weekly", "1. Do the thing.", "first version")
    org.retire_service(ROOT, "ceo", "weekly", "not needed")
    kinds = [e["kind"] for e in read_events(org) if e["kind"].startswith("service.")]
    assert kinds == ["service.define", "service.define", "service.revise", "service.retire"]
    first, second = read_events(org, "service.define")
    assert (first["owner"], first["service"], first["version"], first["by"], first["amendment"]) == ("ceo", "weekly", 1, "root", False)
    assert second["version"] == 2 and second["amendment"] is True
    (rev,) = read_events(org, "service.revise")
    assert rev["version"] == 1 and rev["by"] == "ceo" and rev["owner"] == "ceo"


def test_review_run_event(org):
    from orgmcp import review

    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    result = review.review(org)
    (ev,) = read_events(org, "review.run")
    assert ev["flagged"] == result.flagged and ev["notes"] == [n.to for n in result.notes]
    review.review(org, dry_run=True)
    assert len(read_events(org, "review.run")) == 1  # a dry run changes nothing and says nothing


def test_cli_command_events(org):
    root = ["--root", str(org.root)]
    main([*root, "status"])
    with pytest.raises(SystemExit):
        main([*root, "send", "nobody", "hi"])
    ok, bad = [e for e in read_events(org, "cli.command")]
    assert (ok["command"], ok["ok"], ok["error"], ok["proc"], ok["actor"]) == ("status", True, None, "cli", "root")
    assert bad["command"] == "send" and bad["ok"] is False and "no such agent" in bad["error"]
    assert bad["error_type"] == "OrgError" and bad["ms"] >= 0


def test_cli_init_records_its_command_in_the_new_org(tmp_path):
    main(["init", str(tmp_path / "brand-new"), "--mission", "m"])
    (ev,) = read_events(Org(tmp_path / "brand-new"), "cli.command")
    assert ev["command"] == "init" and ev["ok"] is True


# ------------------------------------------------------------------------------- scheduler: runs, through tools
def test_a_real_run_shows_start_end_tool_calls_and_traces(org):
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=8)
    run_all(org, "tools")
    starts, ends = read_events(org, "run.start"), read_events(org, "run.end")
    assert len(starts) == len(ends) == org.runs_used("ceo") + org.runs_used("ceo/eng") == 3
    assert {s["run"] for s in starts} == {e["run"] for e in ends}
    for s in starts:
        assert re.fullmatch(r"ceo(/eng)?@\d{8}T\d{12}", s["run"]) and s["run"].split("@")[0] == s["agent"]
        assert s["traces"] == [task.id] and s["trace"] == task.id and s["batch"] and s["child_pid"] == s["pgid"] > 0
        assert s["pid"] == os.getpid()  # the envelope pid is the scheduler's own
        assert s["proc"] == "scheduler" and s["actor"] == "runtime" and s["budget_before"] >= 1
        assert (org.dir(s["agent"]) / "runs" / f"{s['run'].split('@')[1]}.log").is_file()
    for e in ends:
        assert e["ok"] is True and e["exit_code"] == 0 and e["duration_ms"] > 0 and e["timed_out"] is False
        assert e["killed"] is False and e["error"] is None and e["trace"] == task.id
    eng = next(e for e in ends if e["agent"] == "ceo/eng")
    eng_start = next(s for s in starts if s["agent"] == "ceo/eng")
    assert eng["budget_after"] == org.budget("ceo/eng") == 0 and eng_start["budget_before"] == 2
    # the MCP-side events of those runs carry the run id and the actor
    calls = read_events(org, "tool.call")
    assert calls and {c["proc"] for c in calls} == {"mcp"}
    by_run = {}
    for c in calls:
        by_run.setdefault(c["run"], []).append(c)
    assert set(by_run) == {s["run"] for s in starts}
    for run_id, cs in by_run.items():
        assert {c["actor"] for c in cs} == {run_id.split("@")[0]}
        assert {c["trace"] for c in cs} == {task.id}
    leaf = by_run[eng_start["run"]]
    refused = [c for c in leaf if not c["ok"]]
    assert [c["tool"] for c in refused] == ["report"] and "status must be one of" in refused[0]["error"]
    assert refused[0]["args"]["summary_chars"] == 5000
    assert [c["tool"] for c in leaf if c["ok"]] == ["whoami", "write", "report"]
    # messages: every one is stamped with the trace and delivered by the agent that sent it
    delivered = read_events(org, "msg.deliver")
    assert {d["trace"] for d in delivered} == {task.id}
    assert {d["actor"] for d in delivered} == {"root", "ceo", "ceo/eng"}
    # scheduler lifecycle
    lifecycle = [e["kind"] for e in read_events(org) if e["kind"] in ("scheduler.start", "scheduler.exit")]
    assert lifecycle == ["scheduler.start", "scheduler.exit"] and read_events(org, "scheduler.heartbeat")


def test_run_events_for_a_crashing_agent_pause_and_failure_chain(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    run_all(org, "crash")
    ends = read_events(org, "run.end")
    assert len(ends) == 3 and all(e["ok"] is False and e["exit_code"] == 1 and e["error"] == "exit code 1" for e in ends)
    assert [e["count"] for e in read_events(org, "agent.failure")] == [1, 2, 3]
    (pause,) = read_events(org, "agent.pause")
    assert pause["agent"] == "ceo" and pause["reason"] == "failures"
    starts = read_events(org, "run.start")
    assert [s["budget_before"] for s in starts] == [10, 9, 8] and [e["budget_after"] for e in ends] == [9, 8, 7]
    # the notice to root about the failing agent belongs to the request
    notice = [m for m in org.received(ROOT) if m.sender == "runtime"][0]
    assert notice.trace == task.id


def test_a_run_that_times_out_is_recorded_as_killed_and_timed_out(org):
    configure(org, run_timeout=0.3)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    sched = Scheduler(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    try:
        for _ in range(100):
            sched.tick()
            if read_events(org, "run.end"):
                break
            time.sleep(0.05)
    finally:
        sched.release()
    end = read_events(org, "run.end")[0]
    assert end["ok"] is False and end["timed_out"] is True and end["killed"] is True
    assert end["exit_code"] == -9 and "timed out" in end["error"] and end["duration_ms"] >= 300


def test_a_run_interrupted_by_shutdown_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    sched = Scheduler(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    sched.tick()
    assert "ceo" in sched.runs
    sched.release()
    end = read_events(org, "run.end")[0]
    assert end["killed"] is True and end["ok"] is False and end["error"] == "interrupted by scheduler shutdown"
    assert read_events(org, "scheduler.exit")[0]["runs_started"] == 1


def test_a_run_of_an_agent_retired_mid_run_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    sched = Scheduler(org, fake_runner("hang"), **SILENT)
    sched.acquire()
    try:
        sched.tick()
        org.retire(ROOT, "ceo", "gone")
        sched._reap()
    finally:
        sched.release()
    end = read_events(org, "run.end")[0]
    assert end["agent"] == "ceo" and end["killed"] is True and end["budget_after"] is None
    assert "retired" in end["error"]


def test_a_run_that_cannot_start_has_a_start_and_an_end(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)

    def runner(o, addr, prompt):
        return ["/nonexistent/binary"], o.dir(addr), dict(os.environ)

    sched = Scheduler(org, runner, **SILENT)
    sched.acquire()
    try:
        sched.tick()
    finally:
        sched.release()
    (start,), (end,) = read_events(org, "run.start"), read_events(org, "run.end")
    assert start["run"] == end["run"] and start["child_pid"] is None
    assert end["ok"] is False and end["error"].startswith("failed to start") and end["exit_code"] is None
    assert read_events(org, "agent.failure")[0]["count"] == 1


def test_the_run_id_reaches_the_agent_process_environment(org, tmp_path):
    out = tmp_path / "env.txt"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    cmd = ["sh", "-c", f'echo "$ORG_RUN_ID" > {out}']

    def runner(o, addr, prompt):
        env = {k: v for k, v in os.environ.items() if k != "ORG_RUN_ID"}
        return cmd, o.dir(addr), env

    sched = Scheduler(org, runner, **SILENT)
    sched.acquire()
    try:
        drain(sched)
    finally:
        sched.release()
    (start,) = read_events(org, "run.start")
    assert out.read_text().strip() == start["run"]


def test_scheduler_start_and_exit_describe_the_mode_and_reason(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    previous = signal.getsignal(signal.SIGTERM)
    try:
        Scheduler(org, fake_runner("work"), **SILENT).serve(until_done=True, max_runs=20)
    finally:
        signal.signal(signal.SIGTERM, previous)
    start, = read_events(org, "scheduler.start")
    assert start["mode"] == "until_done" and start["max_runs"] == 20 and start["max_parallel"] == 3
    assert start["version"] and start["proc"] == "scheduler" and start["actor"] == "runtime"
    exit_, = read_events(org, "scheduler.exit")
    assert exit_["reason"] == "finished: no open tasks" and exit_["runs_started"] == 3


def test_until_idle_and_once_modes(org):
    previous = signal.getsignal(signal.SIGTERM)
    try:
        Scheduler(org, fake_runner("work"), **SILENT).serve(until_idle=True)
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert read_events(org, "scheduler.start")[0]["mode"] == "until_idle"
    assert read_events(org, "scheduler.exit")[0]["reason"].startswith("idle")
    sched = Scheduler(org, fake_runner("work"), **SILENT)
    sched.mode = "once"
    sched.acquire()
    sched.release()
    assert read_events(org, "scheduler.start")[-1]["mode"] == "once"


def test_an_error_in_serve_is_the_exit_reason(org):
    class Broken(MemoryFailureCounter):
        def repair(self):
            return 1 / 0

    sched = Scheduler(org, fake_runner("work"), ports={FailureCounter: Broken()}, **SILENT)
    previous = signal.getsignal(signal.SIGTERM)
    try:
        with pytest.raises(ZeroDivisionError):
            sched.serve(until_idle=True)
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert read_events(org, "scheduler.exit")[0]["reason"].startswith("error: ZeroDivisionError")


def test_heartbeat_lists_running_runs_and_what_waits(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=4)
    org.send("ceo", ROOT, "need a decision")
    clock = Clock()
    sched = Scheduler(org, fake_runner("hang"), clock=clock, **SILENT)
    sched.acquire()
    try:
        sched.tick()
        assert len(read_events(org, "scheduler.heartbeat")) == 1
        sched.tick()
        assert len(read_events(org, "scheduler.heartbeat")) == 1  # not before heartbeat_seconds
        clock.advance(61)
        sched.tick()
        beats = read_events(org, "scheduler.heartbeat")
        assert len(beats) == 2
        (run_id,) = [r.run_id for r in sched.runs.values()]
        assert beats[-1]["running"] == [run_id] and beats[-1]["runnable"] == 0 and beats[-1]["waiting_on_you"] == 1
    finally:
        sched.release()


def test_heartbeat_interval_is_configurable(org):
    configure(org, heartbeat_seconds=5)
    clock = Clock()
    sched = Scheduler(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.tick()
    clock.advance(6)
    sched.tick()
    assert len(read_events(org, "scheduler.heartbeat")) == 2


def test_a_failing_phase_is_an_error_event_once_per_change(org):
    ladder = ScriptedLadder()
    ladder.fail = RuntimeError("kaput")
    sched = Scheduler(org, fake_runner("idle"), ports={StallLadder: ladder}, **SILENT)
    for _ in range(4):
        sched.tick()
    errors = read_events(org, "scheduler.error")
    assert len(errors) == 1
    assert errors[0]["phase"] == "stall check" and errors[0]["error"] == "RuntimeError: kaput"


def test_budget_pause_events_and_notice_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=1)
    org.start_run_log("ceo")  # the one run is already used up
    sched = Scheduler(org, fake_runner("idle"), **SILENT)
    sched.tick()
    (pause,) = read_events(org, "agent.pause")
    assert pause["agent"] == "ceo" and pause["reason"] == "budget" and pause["actor"] == "runtime"
    notice = [m for m in org.received(ROOT) if m.sender == "runtime"][0]
    assert notice.trace == task.id
    org.send(ROOT, "ceo", "more", budget=3)
    sched.tick()
    assert read_events(org, "agent.resume")[0]["reason"] == "budget is back"
    sched.release()


def test_orphan_recovery_is_recorded_with_the_run_id_of_the_dead_run(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    log = org.start_run_log("ceo")
    victim = subprocess.Popen(["sleep", "60"], start_new_session=True)
    try:
        from orgmcp.scheduler import _start_time

        org.save_ledger("running", {"ceo": {"pgid": victim.pid, "lstart": _start_time(victim.pid), "started": time.time(),
                                            "scheduler": 999999, "log": str(log.relative_to(org.root))}})
        sched = Scheduler(org, fake_runner("idle"), **SILENT)
        sched.acquire()
        sched.release()
        (orphan,) = read_events(org, "run.orphan")
        assert orphan["agent"] == "ceo" and orphan["run"] == f"ceo@{log.stem}" and orphan["action"] == "killed"
        assert orphan["detail"] and victim.wait(timeout=10) == -signal.SIGKILL
    finally:
        if victim.poll() is None:
            victim.kill()
            victim.wait()


def test_orphan_that_cannot_be_verified_is_kept(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    log = org.start_run_log("ceo")
    victim = subprocess.Popen(["sleep", "60"], start_new_session=True)
    try:
        org.save_ledger("running", {"ceo": {"pgid": victim.pid, "lstart": None, "started": time.time(),
                                            "scheduler": 999999, "log": str(log.relative_to(org.root))}})
        sched = Scheduler(org, fake_runner("idle"), **SILENT)
        sched.acquire()
        sched.tick()
        sched.release()
        orphans = read_events(org, "run.orphan")
        assert [o["action"] for o in orphans] == ["kept"]  # reported once, not on every tick
    finally:
        victim.kill()
        victim.wait()


def test_runs_counted_in_events_match_the_run_logs(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    run_all(org, "work")
    logs = {f"{a}@{p.stem}" for a in ("ceo", "ceo/eng") for p in (org.dir(a) / "runs").glob("*.log")}
    assert {s["run"] for s in read_events(org, "run.start")} == logs == {e["run"] for e in read_events(org, "run.end")}


def test_every_line_of_a_full_run_is_valid_and_gapless(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    run_all(org, "tools")
    for f in event_files(org):
        events = [json.loads(line) for line in f.read_text().splitlines()]
        assert [e["seq"] for e in events] == list(range(1, len(events) + 1)), f.name
        assert {e["v"] for e in events} == {1}
        for e in events:
            assert {"ts", "proc", "pid", "kind", "actor", "run", "trace"} <= set(e)
            assert len(json.dumps(e).encode()) <= telemetry.LINE_MAX


def test_scheduler_runs_work_with_events_off(org):
    configure(org, events=False)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    run_all(org, "work")
    assert (org.root / "ceo/eng/work/out.md").is_file()
    assert not (org.root / ".runtime" / "events").exists()
