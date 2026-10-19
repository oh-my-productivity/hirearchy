"""Acceptance of observability (spec section 1, "done means"), on the REAL emitter: no synthetic events.

A real organization (root -> ceo -> eng) is run by the real scheduler with the fake agent in its ``tools`` mode (it calls
the orgmcp MCP tools in-process, so the real server records ``tool.call``). The story has one refused tool call (eng's
``report`` with a bad status, every time), one crashed run (eng's first run exits 1) and one rework (root revises its
task). Every expectation is derived independently from the files (run logs, messages, raw event lines), then compared
with what the views say.
"""

import asyncio
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from testkit.scheduler import scheduler_is

from orgmcp import observe, telemetry
from orgmcp.cli import main
from orgmcp.core import ROOT, Message, Org
from orgmcp.progress import progress
from orgmcp.scheduler import Scheduler, SchedulerState
from orgmcp.server import build_server

FAKE = str(Path(__file__).with_name("fake_agent.py"))
REFUSAL = "status must be one of ('done', 'failed', 'blocked')"


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def runner_with(once: dict[str, str]):
    """The fake agent in ``tools`` mode; ``once[agent]`` overrides the mode of that agent's next run only."""

    def build(org, addr, prompt):
        mode = once.pop(addr, "tools")
        return [sys.executable, FAKE], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    return build


def drain(sched, limit=90.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.02)
    assert time.time() < deadline, "organization never went idle"


def new_org(base: Path) -> Org:
    o = Org.init(base / "org", "Observe me", {"poll_seconds": 0.05})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


# ------------------------------------------------------------------------------------------ independent readers


def raw_events(org: Org) -> list[dict]:
    """Every event line, read straight from the files (never through the query layer)."""
    out = []
    for f in sorted((org.root / ".runtime" / "events").glob("*/*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))
    return sorted(out, key=lambda e: e["ts"])


def run_logs(org: Org) -> list[str]:
    """Run ids from the run logs on disk: the file truth of 'a run happened'."""
    return sorted(f"{a}@{p.stem}" for a in org.agents() for p in (org.dir(a) / "runs").glob("*.log"))


def message_ids(org: Org) -> set[str]:
    """Ids of every message ever sent (the sender's copies)."""
    return {p.stem for a in (ROOT, *org.agents()) for p in (org.dir(a) / "sent").glob("*.md")}


def progress_runs(org: Org, task_id: str) -> tuple[int, int]:
    m = re.search(r"runs (\d+) of (\d+)", progress(org, task_id).splitlines()[0])
    assert m, progress(org, task_id)
    return int(m.group(1)), int(m.group(2))


def cli_out(capsys, *argv) -> str:
    capsys.readouterr()
    main(list(argv))
    return capsys.readouterr().out


# ------------------------------------------------------------------------------------------ the world


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    base = tmp_path_factory.mktemp("obs-e2e")
    mp.setenv("HOME", str(base / "home"))  # nothing here may touch the real home
    telemetry.reset()
    org = new_org(base)
    root = build_server(org, ROOT)
    once = {"ceo/eng": "crash"}  # eng's first run crashes; the scheduler retries it
    sched = Scheduler(org, runner_with(once), echo=lambda _: None)
    sched.acquire()
    try:
        call(root, "delegate", to="ceo", title="Ship it", goal="Ship the thing", acceptance="It is shipped", budget=8)
        first = next(m for m in org.sent(ROOT) if m.type == "task")
        drain(sched)
        call(root, "delegate", to="ceo", title="Ship it better", goal="Ship the thing, better", acceptance="Shipped well",
             budget=6, revises=first.id)
        second = max((m for m in org.sent(ROOT) if m.type == "task"), key=lambda m: m.id)
        drain(sched)
    finally:
        sched.release()
        telemetry.reset()
    yield SimpleNamespace(org=org, first=first, second=second, base=base)
    mp.undo()


@pytest.fixture
def copy_of_world(world, tmp_path):
    """A throwaway copy of the finished organization, for tests that corrupt it."""
    dst = tmp_path / "org"
    shutil.copytree(world.org.root, dst)
    old = time.time() - 3600  # "an hour ago": nothing is still being delivered
    for p in dst.rglob("*"):
        if p.is_file():
            os.utime(p, (old, old))
    return Org(dst)


def test_the_story_really_happened(world):
    """Guards the scenario itself: a crash, a refusal, a rework, all done."""
    org, ev = world.org, raw_events(world.org)
    assert progress_runs(org, world.first.id)[0] + progress_runs(org, world.second.id)[0] == len(run_logs(org)) == 7
    ends = [e for e in ev if e["kind"] == "run.end"]
    assert [e["error"] for e in ends if not e["ok"]] == ["exit code 1"]
    refused = [e for e in ev if e["kind"] == "tool.call" and e["ok"] is False]
    assert len(refused) == 2 and all(REFUSAL in e["error"] for e in refused)
    assert "done" in progress(org, world.first.id) and "done" in progress(org, world.second.id)
    assert ".runtime/events/" in (org.root / ".gitignore").read_text()


# ------------------------------------------------------------------------------------------ Q2, Q3: trace


def test_trace_lists_every_run_message_tool_call_and_refusal(world):
    org = world.org
    tr = observe.trace(org, world.first.id)
    assert not tr["partial"] and tr["state"] == "done"
    ev = raw_events(org)

    # every run of every agent in the tree, with queue wait and duration
    runs = [i for i in tr["items"] if i["kind"] == "run"]
    assert sorted(r["run"] for r in runs) == run_logs(org)
    assert all(r["source"] == "events" and r["queue_ms"] is not None and r["queue_ms"] >= 0 for r in runs)
    assert all(r["duration_ms"] and r["duration_ms"] > 0 for r in runs)
    ends = {e["run"]: e for e in ev if e["kind"] == "run.end"}
    assert {r["run"]: r["duration_ms"] for r in runs} == {k: float(v["duration_ms"]) for k, v in ends.items()}
    assert sorted(r["outcome"] for r in runs) == ["failed"] + ["ok"] * 6
    (crashed,) = [r for r in runs if r["outcome"] == "failed"]
    assert crashed["agent"] == "ceo/eng" and crashed["error"] == "exit code 1"

    # every message
    assert {i["id"] for i in tr["items"] if i["kind"] == "message"} == message_ids(org)

    # every orgmcp tool call of those runs (ok or refused) and the refusal text
    calls = [e for e in ev if e["kind"] == "tool.call" and (e["run"] in {r["run"] for r in runs} or e["trace"] == world.first.id)]
    assert tr["totals"]["tool_calls"] == len(calls) and len(calls) >= 18
    per_run = {r["run"]: r["tool_calls"]["total"] for r in runs}
    for rid, n in per_run.items():
        assert n == len([e for e in calls if e["run"] == rid])
    refusals = [r for run in runs for r in run["tool_calls"]["refused"]]
    assert len(refusals) == tr["totals"]["refusals"] == 2
    assert all(r["tool"] == "report" and REFUSAL in r["error"] and r["actor"] == "ceo/eng" for r in refusals)
    text = observe.render_trace(tr)
    assert f"! report: {REFUSAL}" in text and "exit code 1" in text and "queued " in text and "ran " in text
    # the root's own MCP calls (it sent both tasks through the real root server) belong to the request
    assert [c["tool"] for c in calls if c["actor"] == ROOT] == ["delegate", "delegate"]


def test_trace_totals_equal_progress(world):
    org = world.org
    tr = observe.trace(org, world.first.id)
    t = tr["totals"]
    per = {x["task"]: x["runs"] for x in t["tasks"]}
    assert per == {world.first.id: progress_runs(org, world.first.id)[0], world.second.id: progress_runs(org, world.second.id)[0]}
    assert t["runs"] == sum(per.values()) == 7
    assert t["budget_given"] == sum(progress_runs(org, x)[1] for x in per) == 14
    assert t["budget_used"] == t["runs"]
    ends = [e for e in raw_events(org) if e["kind"] == "run.end"]
    assert t["run_ms"] == pytest.approx(sum(e["duration_ms"] for e in ends))
    assert t["queue_ms"] > 0 and t["wall_ms"] > 0 and t["user_wait_ms"] == 0
    # the whole request answers to either of its tasks; so does a message deep inside it
    assert observe.trace(org, world.second.id)["totals"] == t
    inner = next(m.id for m in org.sent("ceo/eng") if m.type == "result")
    assert observe.trace(org, inner)["task"] == world.first.id
    assert re.search(r"tasks: .* 4 run\(s\) \| .* 3 run\(s\)", observe.render_trace(tr))


def test_messages_carry_the_trace_stamped_by_the_runtime(world):
    org = world.org
    msgs = [Message.load(p) for a in (ROOT, *org.agents()) for p in (org.dir(a) / "sent").glob("*.md")]
    assert msgs and {m.trace for m in msgs} == {world.first.id}  # the rework stays in the trace of the task it revises
    delivered = [e for e in raw_events(org) if e["kind"] == "msg.deliver"]
    assert {e["trace_rule"] for e in delivered} <= {"new", "link", "open-task", "batch", "given"} and {"new", "link"} <= {
        e["trace_rule"] for e in delivered}
    assert {d["trace"] for d in delivered} == {world.first.id}


def test_root_grants_and_notes_without_a_trace_still_belong_to_the_request(world, tmp_path):
    """Root's grants/notes may be untraced; the trace attributes them to the request by progress' window rule."""
    base = tmp_path / "grant"
    base.mkdir()
    org = new_org(base)
    task = org.delegate(ROOT, "ceo", "Ship it", "g", "a", budget=3)
    sched = Scheduler(org, runner_with({}), echo=lambda _: None)
    sched.acquire()
    try:
        drain(sched)
    finally:
        sched.release()
    org.send(ROOT, "ceo", "A little more room for this.", budget=2)  # a plain grant: no reply_to, so no trace
    note = next(m for m in org.sent(ROOT) if m.type == "note")
    assert note.trace is None
    tr = observe.trace(org, task.id)
    grants = [i for i in tr["items"] if i["kind"] == "message" and i["id"] == note.id]
    assert len(grants) == 1 and grants[0]["trace_source"] == "window"
    assert tr["totals"]["budget_given"] == 5
    telemetry.reset()


# ------------------------------------------------------------------------------------------ Q5: events


def test_events_errors_has_every_refusal_and_the_crash(world, capsys):
    org = world.org
    out = cli_out(capsys, "--root", str(org.root), "obs", "events", "--errors", "--since", "1h", "--json")
    got = [json.loads(line) for line in out.strip().splitlines()]
    refusals = [e for e in got if e["kind"] == "tool.call"]
    expected = [e for e in raw_events(org) if e["kind"] == "tool.call" and e["ok"] is False]
    assert [e["error"] for e in refusals] == [e["error"] for e in expected] and len(refusals) == 2
    assert all(REFUSAL in e["error"] and e["error_type"] == "OrgError" and e["actor"] == "ceo/eng" for e in refusals)
    crash = [e for e in got if e["kind"] == "run.end"]
    assert len(crash) == 1 and crash[0]["error"] == "exit code 1" and crash[0]["agent"] == "ceo/eng" and crash[0]["ok"] is False
    assert any(e["kind"] == "agent.failure" for e in got)
    text = cli_out(capsys, "--root", str(org.root), "obs", "events", "--errors", "--since", "1h")
    assert text.count("REFUSED") == 2 and REFUSAL in text and "exit code 1" in text


def test_events_filters_by_trace_agent_and_kind(world):
    org = world.org
    by_trace = observe.events(org, trace=world.first.id, since="1h")
    assert by_trace and all(e["trace"] == world.first.id or world.first.id in (e.get("traces") or []) for e in by_trace)
    assert {e["actor"] for e in observe.events(org, agent="ceo/eng", kind="tool.call", since="1h")} == {"ceo/eng"}
    assert {e["kind"] for e in observe.events(org, kind="run", since="1h")} == {"run.start", "run.end"}


# ------------------------------------------------------------------------------------------ Q4: metrics


def test_metrics_counts_equal_counts_derived_from_the_files(world, capsys):
    org = world.org
    m = json.loads(cli_out(capsys, "--root", str(org.root), "obs", "metrics", "--since", "1h", "--by", "agent", "--json"))
    ev = raw_events(org)
    logs = run_logs(org)
    assert m["runs"]["total"] == len(logs) == 7
    ends = [e for e in ev if e["kind"] == "run.end"]
    assert (m["runs"]["ok"], m["runs"]["failed"], m["runs"]["timeout"], m["runs"]["killed"]) == (
        sum(e["ok"] for e in ends), sum(not e["ok"] for e in ends), 0, 0) == (6, 1, 0, 0)
    per_agent = {r["key"]: r["runs"] for r in m["by"]["rows"] if r["runs"]}
    assert per_agent == {a: len([x for x in logs if x.startswith(a + "@")]) for a in ("ceo", "ceo/eng")}
    calls = [e for e in ev if e["kind"] == "tool.call"]
    tc = m["tool_calls"]
    assert tc["total"] == len(calls) and tc["refused"] == len([e for e in calls if not e["ok"]]) == 2
    assert {k: v["calls"] for k, v in tc["by_tool"].items()} == {t: len([e for e in calls if e["tool"] == t]) for t in {e["tool"] for e in calls}}
    assert {k: v["refused"] for k, v in tc["by_tool"].items() if v["refused"]} == {"report": 2}
    (top,) = m["top_refusals"]
    assert top["count"] == 2 and top["example"] == REFUSAL and top["tools"] == {"report": 2}
    types = {}
    for p in (org.dir(a) / "sent" for a in (ROOT, *org.agents())):
        for f in p.glob("*.md"):
            t = Message.load(f).type
            types[t] = types.get(t, 0) + 1
    assert m["messages"] == types
    assert m["agent_failures"] == 1 and m["budget_spent"] == 7
    assert m["runs"]["duration_ms"]["n"] == 7 and m["runs"]["queue_ms"]["n"] == 7
    text = observe.render_metrics(observe.metrics(org, "1h"))
    assert "report" in text and "2 refused" in text


# ------------------------------------------------------------------------------------------ Q6: check


def test_check_passes_on_a_healthy_org(world, capsys):
    res = observe.check(world.org)
    assert res["ok"], observe.render_check(res)
    assert [c["id"] for c in res["checks"]] == list("abcdef") and all(c["ok"] for c in res["checks"])
    out = cli_out(capsys, "--root", str(world.org.root), "check")
    assert "all checks passed" in out
    assert "all checks passed" in call(build_server(world.org, ROOT), "observe", view="check")


def failing(org, check_id, also=()):
    """The details of check ``check_id``, which must FAIL (as must ``also``, the checks it drags along); the rest pass."""
    res = observe.check(org)
    assert not res["ok"]
    bad = {c["id"]: c for c in res["checks"] if not c["ok"]}
    assert set(bad) == {check_id, *also}, observe.render_check(res)
    return "\n".join(bad[check_id]["details"])


def test_check_names_a_lost_message_copy(copy_of_world, capsys):
    org = copy_of_world
    victim = next(p for p in (org.dir("ceo") / "read").glob("*.md") if Message.load(p).type == "task")
    mid = victim.stem
    victim.unlink()
    assert mid in failing(org, "a", also="b")  # the run budget that message carried is gone too
    with pytest.raises(SystemExit) as exc:
        main(["--root", str(org.root), "check"])
    out = capsys.readouterr().out
    assert exc.value.code == 1 and "FAIL" in out and mid in out


def test_check_names_a_broken_budget(world, copy_of_world):
    org = copy_of_world
    path = org.dir(ROOT) / "sent" / f"{world.first.id}.md"
    assert "budget: 8" in path.read_text(encoding="utf-8")
    path.write_text(path.read_text(encoding="utf-8").replace("budget: 8", "budget: 80", 1), encoding="utf-8")
    assert "handed down" in failing(org, "b")


def test_check_names_a_run_with_no_end(copy_of_world):
    org = copy_of_world
    run = next(e["run"] for e in raw_events(org) if e["kind"] == "run.end" and e["agent"] == "ceo/eng" and e["ok"])
    for f in (org.root / ".runtime" / "events").glob("*/scheduler-*.jsonl"):
        keep = [ln for ln in f.read_text(encoding="utf-8").splitlines()
                if not (json.loads(ln)["kind"] == "run.end" and json.loads(ln)["run"] == run)]
        f.write_text("\n".join(keep) + "\n", encoding="utf-8")
    detail = failing(org, "d", also="e")  # the removed line also leaves a hole in that file's seq
    assert run in detail and "no run.end" in detail


def test_check_names_a_lost_event_line(copy_of_world):
    org = copy_of_world
    f = max((org.root / ".runtime" / "events").glob("*/mcp-*.jsonl"), key=lambda p: len(p.read_text().splitlines()))
    lines = f.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 4
    del lines[2]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    detail = failing(org, "e")
    assert f.name in detail and "lost" in detail


def test_check_names_a_stuck_inflight_batch(copy_of_world):
    org = copy_of_world
    some = next(org.dir("ceo/eng").joinpath("read").glob("*.md"))
    inflight = org.dir("ceo/eng") / "inflight"
    inflight.mkdir(exist_ok=True)
    shutil.move(str(some), str(inflight / some.name))
    os.utime(inflight / some.name, (time.time() - 3600, time.time() - 3600))
    assert "ceo/eng" in failing(org, "c")


# ------------------------------------------------------------------------------------------ Q1: now


def test_now_reflects_a_running_and_a_queued_state(tmp_path, capsys):
    telemetry.reset()
    org = new_org(tmp_path)
    root = build_server(org, ROOT)
    once = {"ceo": "hang"}
    sched = Scheduler(org, runner_with(once), echo=lambda _: None)
    sched.acquire()
    mp = pytest.MonkeyPatch()
    try:
        call(root, "delegate", to="ceo", title="Slow job", goal="g", acceptance="a", budget=3)
        hang = next(m for m in org.sent(ROOT) if m.type == "task")
        deadline = time.time() + 20
        while not org.running("ceo") and time.time() < deadline:
            sched.tick()
            time.sleep(0.05)
        assert org.running("ceo")
        call(root, "delegate", to="ceo", title="Second job", goal="g", acceptance="a", budget=2)  # waits behind the run
        sched.tick()
        # this pytest process stands in for the scheduler process: tell the view its pid file is verified
        scheduler_is(mp, SchedulerState("running", os.getpid(), "now"), org)
        time.sleep(0.3)
        v = observe.now_view(org)
        assert v["scheduler"]["state"] == "running" and v["scheduler"]["mode"] == "daemon"
        (r,) = v["runs_in_flight"]
        assert r["agent"] == "ceo" and r["batch"] == ["Slow job"] and r["traces"] == [hang.id] and r["elapsed_s"] > 0
        assert r["run"] in run_logs(org)
        (q,) = v["queued"]
        assert q["agent"] == "ceo" and q["unread"] == 1 and "current run" in q["reason"]
        text = cli_out(capsys, "--root", str(org.root), "obs", "now")
        assert "scheduler: running" in text and "runs in flight 1/3" in text and "Slow job" in text and hang.id in text
        assert "ceo: 1 unread" in text
        assert "runs in flight 1/3" in call(root, "observe", view="now")
        assert "ceo" in observe.trace(org, hang.id)["team"]
    finally:
        mp.undo()
        sched.release()  # kills the hung run: its cause is recorded
        telemetry.reset()
    ended = [e for e in raw_events(org) if e["kind"] == "run.end"]
    assert len(ended) == 1 and ended[0]["killed"] is True and "shutdown" in ended[0]["error"]
    after = observe.trace(org, hang.id)
    (run,) = [i for i in after["items"] if i["kind"] == "run"]
    assert run["outcome"] == "killed" and "shutdown" in run["error"]
    assert "scheduler.exit" in {e["kind"] for e in raw_events(org)}
    assert "killed" in cli_out(capsys, "--root", str(org.root), "obs", "events", "--errors", "--since", "1h")
    assert observe.check(org)["ok"], observe.render_check(observe.check(org))


def test_now_with_a_stale_running_record_and_no_scheduler(tmp_path):
    """A crafted running.json (a dead scheduler's run): visible, never a crash of the view."""
    org = new_org(tmp_path)
    org.delegate(ROOT, "ceo", "Orphaned", "g", "a", budget=2)
    org.begin_run("ceo")
    log = org.start_run_log("ceo")
    (org.root / ".runtime" / "running.json").write_text(json.dumps({"ceo": {
        "pgid": 999999, "lstart": "Mon Jan  1 00:00:00 2001", "started": time.time() - 30, "scheduler": 999998,
        "log": str(log.relative_to(org.root))}}), encoding="utf-8")
    v = observe.now_view(org)
    assert v["scheduler"]["state"] == "stopped"
    assert [r["agent"] for r in v["runs_in_flight"]] == ["ceo"]
    res = observe.check(org)
    assert not res["ok"] and any(c["id"] == "c" and not c["ok"] for c in res["checks"])
    telemetry.reset()
