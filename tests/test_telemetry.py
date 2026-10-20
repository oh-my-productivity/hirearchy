"""The event log (emission side): files, envelope, safety, retention, trace stamping and every emitted kind."""

import asyncio
import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import testkit

from orgmcp import telemetry
from orgmcp.core import ROOT, Message, Org, join_frontmatter, split_frontmatter
from orgmcp.kernel.testing import FakeClock
from orgmcp.scheduler import Scheduler, ignore_runtime_files
from orgmcp.server import build_server
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


def call(server, tool, **args):
    return asyncio.run(server.call_tool(tool, args))


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


# ------------------------------------------------------------------------------------------------- tool.call
def agent_server(org, me="ceo"):
    return build_server(org, me)


def test_tool_calls_are_recorded_with_actor_run_and_summary(org, monkeypatch):
    monkeypatch.setenv("ORG_RUN_ID", "ceo@20260101T000000000000")
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    call(server, "whoami")
    call(server, "delegate", to="ceo/eng", title="Build it", goal="g" * 3000, acceptance="a" * 200, budget=2)
    calls = read_events(org, "tool.call")
    assert [c["tool"] for c in calls] == ["whoami", "delegate"]
    who, deleg = calls
    assert who["ok"] is True and who["error"] is None and who["error_type"] is None and who["ms"] >= 0
    assert who["proc"] == "mcp" and who["actor"] == "ceo" and who["run"] == "ceo@20260101T000000000000"
    assert who["trace"] == task.id  # the one trace of the caller's batch
    assert deleg["args"] == {"to": "ceo/eng", "title": "Build it", "budget": 2, "goal_chars": 3000, "acceptance_chars": 200}
    assert deleg["trace"] == task.id


def test_every_refusal_is_recorded_and_the_tool_still_raises_the_same(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    with pytest.raises(Exception) as info:
        call(server, "delegate", to="ceo", title="x", goal="g", acceptance="a")
    assert "direct reports" in str(info.value)
    with pytest.raises(Exception) as bad:
        call(server, "report", task_id="no-such-task", status="done", summary="s")
    assert "no task no-such-task assigned to you" in str(bad.value)
    refused = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert [c["tool"] for c in refused] == ["delegate", "report"]
    assert all(c["error_type"] == "OrgError" and c["error"] for c in refused)
    assert "you can only delegate to your direct reports" in refused[0]["error"]
    assert refused[1]["args"]["task_id"] == "no-such-task" and refused[1]["args"]["status"] == "done"


def test_a_refusal_keeps_the_trace_of_the_task_it_names(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    org.report("ceo", task.id, "done", "ok")
    with pytest.raises(Exception):
        call(agent_server(org), "report", task_id=task.id, status="done", summary="again")
    bad = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert bad[0]["trace"] == task.id and "final" in bad[0]["error"]


def test_unexpected_exceptions_are_recorded_by_class(org):
    import dataclasses

    from orgmcp.overview import OrgTree

    class BrokenTree(OrgTree):  # the tree of the status tool is the port of the runtime, not a method of the facade
        def tree(self) -> str:
            return 1 / 0

    org.runtime = dataclasses.replace(org.runtime, org_tree=BrokenTree())
    server = agent_server(org)
    with pytest.raises(Exception):
        call(server, "status")
    (bad,) = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert bad["error_type"] == "ZeroDivisionError" and "division" in bad["error"]


def test_bodies_never_reach_the_log_only_their_length(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    secret = "TOPSECRET" + "z" * 4991
    call(server, "send", to="ceo/eng", body=secret, title="t" * 200)
    call(server, "write", path="ceo/work/n.md", content=secret)
    call(server, "report", task_id=task.id, status="done", summary=secret, lessons=secret[:700], artifacts=["ceo/work/n.md"])
    sent, wrote, reported = read_events(org, "tool.call")[:3]
    assert sent["args"]["body_chars"] == 5000 and "body" not in sent["args"]
    assert len(sent["args"]["title"]) == 80 and sent["args"]["to"] == "ceo/eng"
    assert wrote["args"] == {"path": "ceo/work/n.md", "content_chars": 5000, "append": False}
    assert reported["args"]["summary_chars"] == 5000 and reported["args"]["lessons_chars"] == 700
    assert reported["args"]["artifacts"] == ["ceo/work/n.md"]
    for f in event_files(org):
        assert "TOPSECRET" not in f.read_text()


def test_a_tool_call_trace_is_that_of_the_message_it_delivered(org):
    a = org.delegate(ROOT, "ceo", "A", "g", "a", budget=8)
    b = org.delegate(ROOT, "ceo", "B", "g", "a", budget=8)
    org.begin_run("ceo")  # two traces in the batch: only the call's own effect can tell
    server = agent_server(org)
    call(server, "report", task_id=b.id, status="done", summary="ok")
    call(server, "whoami")
    report, who = read_events(org, "tool.call")
    assert report["trace"] == b.id and who["trace"] is None
    assert a.id != b.id


def test_arg_summaries_by_type():
    out = telemetry.summarize_args({
        "to": "ceo", "budget": 3, "append": True, "n": None, "blob": "x" * 500, "inputs": {"topic": "secret", "k": "v"},
        "acceptance": ["one", "two"], "tools": ["read", "write"], "artifacts": ["a.md"], "obj": object(), "name": "n" * 200,
    })
    assert out["to"] == "ceo" and out["budget"] == 3 and out["append"] is True and "n" not in out
    assert out["blob_chars"] == 500 and "blob" not in out
    assert out["inputs_keys"] == ["topic", "k"] and "secret" not in json.dumps(out)
    assert out["acceptance_n"] == 2 and out["acceptance_chars"] == 6
    assert out["tools"] == ["read", "write"] and out["artifacts"] == ["a.md"]
    assert out["obj_type"] == "object" and len(out["name"]) == 80


def test_every_tool_of_every_role_is_instrumented(org, tmp_path):
    org.define_service(ROOT, "ceo", "weekly", description="A brief.", acceptance=["Short"],
                       deliverable={"description": "one file"}, budget=4)
    servers = {
        "root": build_server(org, ROOT),
        "manager": build_server(org, "ceo"),  # also offers a service: owner tools
        "worker": build_server(org, "ceo/eng"),
    }
    seen = set()
    for who, server in servers.items():
        for tool in server._tool_manager.list_tools():
            assert hasattr(tool.fn, "__wrapped__"), f"{who}: {tool.name} is not recorded"
            seen.add(tool.name)
    for name in ("whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status",
                 "health", "services", "define_service", "request", "feedback", "revise_playbook", "create_org", "start",
                 "stop", "blueprint_example", "propose_org", "apply_org", "progress"):
        assert name in seen, name


def test_tools_keep_their_names_signatures_and_docstrings(org):
    import inspect

    tools = {t.name: t for t in build_server(org, "ceo")._tool_manager.list_tools()}
    delegate = tools["delegate"]
    assert delegate.description.startswith("Assign a task to one of your direct reports.")
    assert list(delegate.parameters["properties"]) == ["to", "title", "goal", "acceptance", "inputs", "budget", "revises"]
    assert list(inspect.signature(delegate.fn).parameters) == ["to", "title", "goal", "acceptance", "inputs", "budget", "revises"]
    assert delegate.fn.__name__ == "delegate"


def test_a_tool_added_later_is_recorded_without_extra_work(org):
    server = build_server(org, ROOT)

    @server.tool()
    def observe_stub(view: str = "now", limit: int = 5) -> str:
        """A stand-in for a tool somebody adds to the server later."""
        return f"viewed {view}"

    call(server, "observe_stub", view="trace")
    (ev,) = read_events(org, "tool.call")
    assert ev["tool"] == "observe_stub" and ev["actor"] == "root" and ev["args"] == {"view": "trace", "limit": 5}


def test_the_async_progress_tool_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    call(build_server(org, ROOT), "progress")
    (ev,) = read_events(org, "tool.call")
    assert ev["tool"] == "progress" and ev["ok"] is True and ev["actor"] == "root"


def test_a_server_without_an_organization_still_works_and_writes_nothing(tmp_path):
    target = tmp_path / "later"
    from orgmcp.server import OrgBinding

    server = build_server(OrgBinding(target), ROOT)
    assert "Setup" in str(call(server, "whoami"))
    assert not target.exists()
    call(server, "create_org", mission="a mission")
    (ev,) = [e for e in read_events(Org(target), "tool.call")]
    assert ev["tool"] == "create_org" and ev["args"] == {"mission_chars": 9}
    assert not any(".runtime/events" in line for line in (target / ".gitignore").read_text().split("\n") if line.startswith("!"))


def test_emission_failure_does_not_change_a_tool_result(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "events").write_text("blocked")
    server = build_server(org, ROOT)
    assert "ceo" in str(call(server, "status"))
    with pytest.raises(Exception) as info:
        call(server, "send", to="nobody", body="x")
    assert "no such agent" in str(info.value)


def test_a_real_mcp_server_process_writes_its_own_events_file(org):
    """The stdio server (``orgmcp mcp``) as kiro starts it: ORG_AGENT and ORG_RUN_ID in its environment."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")

    async def session():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "orgmcp", "mcp"],
            env={**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": "ceo", "ORG_RUN_ID": "ceo@20260101T000000000000"},
        )
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                await s.call_tool("whoami", {})
                refused = await s.call_tool("send", {"to": "nobody", "body": "a secret body"})
                assert refused.isError

    asyncio.run(session())
    mcp_files = [f for f in event_files(org) if f.name.startswith("mcp-")]
    assert len(mcp_files) == 1 and f"-{os.getpid()}-" not in mcp_files[0].name
    who, bad = [json.loads(line) for line in mcp_files[0].read_text().splitlines()]
    assert (who["proc"], who["tool"], who["actor"], who["run"], who["trace"]) == ("mcp", "whoami", "ceo", "ceo@20260101T000000000000", task.id)
    assert bad["ok"] is False and bad["error"] == "no such agent: nobody" and bad["args"] == {"to": "nobody", "body_chars": 13, "title": "", "budget": 0}
    assert (who["seq"], bad["seq"]) == (1, 2) and who["pid"] != os.getpid()
