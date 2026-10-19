"""The query half of observability: events, now, trace, metrics, check, the CLI and the MCP tool.

Event files are written by hand (tests/obs_fixtures.py) exactly per the spec; the emitting module is not imported.
"""

import asyncio
import dataclasses
import json
import os
import re
import sys
import time
from datetime import timedelta
from pathlib import Path

import pytest
from obs_fixtures import T0, EventLog, Story, freeze, run_ids, stamp, stamp_trace

from orgmcp import observe
from orgmcp.cli import main
from orgmcp.core import ROOT, Message, Org, OrgError
from orgmcp.kernel.testing import FakeClock
from orgmcp.progress import progress
from orgmcp.scheduler import Scheduler, SchedulerState
from orgmcp.server import build_server

FAKE = str(Path(__file__).with_name("fake_agent.py"))
NOW = stamp(200)


@pytest.fixture
def org(tmp_path):
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(monkeypatch):
    return freeze(monkeypatch)


@pytest.fixture
def story(org, clock):
    return Story(org, clock)


def sched_org(org, tasks=1, mode="work"):
    """A real scheduler run on the fake agents (real run logs, real messages, no events)."""

    def runner(o, addr, prompt):
        return [sys.executable, FAKE], o.dir(addr), {**os.environ, "ORG_ROOT": str(o.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    made = [org.delegate(ROOT, "ceo", f"Job {i}", "goal", "criteria", budget=6) for i in range(tasks)]
    s = Scheduler(org, runner, echo=lambda _: None)
    s.acquire()
    try:
        for _ in range(500):
            if not s.tick():
                break
            time.sleep(0.02)
    finally:
        s.release()
    return made


# ------------------------------------------------------------------------------------------------ helpers


def test_percentile_is_nearest_rank_and_exact():
    vals = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert observe.percentile(vals, 50) == 50
    assert observe.percentile(vals, 95) == 100
    assert observe.percentile(vals, 10) == 10
    assert observe.percentile([7], 95) == 7
    assert observe.percentile([], 50) is None
    assert observe.percentile([3, 1, 2], 50) == 2  # unsorted input


def test_parse_when_accepts_durations_and_iso():
    now = stamp(0)
    assert observe.parse_when("15m", now) == now - timedelta(minutes=15)
    assert observe.parse_when("24h", now) == now - timedelta(hours=24)
    assert observe.parse_when("7d", now) == now - timedelta(days=7)
    assert observe.parse_when("2026-10-18T09:00:00Z", now) == stamp(-3600)
    assert observe.parse_when("2026-10-18T09:00:00", now) == stamp(-3600)  # naive = UTC
    assert observe.parse_when(None, now) is None and observe.parse_when("", now) is None
    with pytest.raises(OrgError, match="cannot read 'soon'"):
        observe.parse_when("soon", now)


def test_duration_and_relative_formats():
    assert [observe.fmt_dur(x) for x in (850, 4200, 42_000, 65_000, 7_380_000)] == ["850ms", "4.2s", "42s", "1m05s", "2h03m"]
    assert [observe.fmt_rel(x) for x in (0, 42_000, 65_000, 7_380_000)] == ["+0s", "+42s", "+1m05s", "+2h03m"]


def test_refusals_are_normalized_so_reasons_group():
    a = observe.normalize_refusal('not enough budget: you have 5 run(s); task 20261018T100003000001-root-ab12 "Ship it" in ceo/work/x.md')
    b = observe.normalize_refusal('not enough budget: you have 9 run(s); task 20261018T110003000001-root-cd34 "Other" in ceo/work/y.md')
    assert a == b and "5" not in a and "Ship" not in a and "ceo/work" not in a
    assert observe.normalize_refusal("zz " * 200).endswith("…")


# ------------------------------------------------------------------------------------------------ events


def test_events_merge_files_by_time_and_tolerate_damage(org):
    log = EventLog(org)
    log.emit("tool.call", stamp(10), proc="mcp", pid=1, actor="ceo", tool="read", ok=True, ms=1, error=None, error_type=None, args={})
    log.emit("run.start", stamp(5), proc="scheduler", pid=2, run="ceo@x", agent="ceo", batch=[], traces=[])
    log.emit("tool.call", stamp(20), proc="mcp", pid=1, actor="ceo", tool="write", ok=True, ms=1, error=None, error_type=None, args={})
    log.emit("scheduler.heartbeat", stamp(15), proc="scheduler", pid=2, running=[], runnable=0, waiting_on_you=0, brand_new_field=1)
    log.emit("kind.from.the.future", stamp(12), proc="cli", pid=3, whatever={"x": 1})
    log.partial_line("mcp", 1, "2026-10-18")  # a line being written
    (org.root / ".runtime" / "events" / "2026-10-18" / "notes.txt").write_text("not an event file")
    (org.root / ".runtime" / "events" / "scratch").mkdir()
    got = observe.events(org, since="2026-10-18T00:00:00Z")
    assert [e["ts"] for e in got] == sorted(e["ts"] for e in got) and len(got) == 5
    assert [e["kind"] for e in got][:2] == ["run.start", "tool.call"]
    assert "kind.from.the.future" in [e["kind"] for e in got]


def test_events_without_any_files_is_empty_not_an_error(org):
    assert observe.events(org) == []
    assert "no matching events" in observe.render_events(observe.events_view(org))


def test_events_time_window_selects_day_directories_first(org):
    log = EventLog(org)
    log.emit("tool.call", stamp(-86400 * 3), actor="ceo", tool="old", ok=True, ms=1)  # 3 days earlier
    log.emit("tool.call", stamp(0), actor="ceo", tool="today", ok=True, ms=1)
    log.emit("tool.call", stamp(86400 * 2), actor="ceo", tool="later", ok=True, ms=1)
    days = {p.parent.name for p in observe.event_files(org, stamp(-3600), stamp(3600))}
    assert days == {"2026-10-18"}
    assert [e["tool"] for e in observe.events(org, since=stamp(-3600), until=stamp(3600))] == ["today"]
    assert [e["tool"] for e in observe.events(org, since="2026-10-10T00:00:00Z", now=stamp(86400 * 3))] == ["old", "today", "later"]


def test_events_filters_and_limit_keep_the_tail(org, story):
    tid = story.task.id
    assert {e["kind"] for e in observe.events(org, kind="run")} == {"run.start", "run.end"}
    assert {e["kind"] for e in observe.events(org, kind="tool.call")} == {"tool.call"}
    assert all(e["actor"] == "ceo/eng" for e in observe.events(org, kind="tool.call", agent="ceo/eng"))
    assert {e["agent"] for e in observe.events(org, kind="run.start", agent="ceo")} == {"ceo"}
    traced = observe.events(org, trace=tid)
    assert traced and all(e["trace"] == tid or tid in (e.get("traces") or []) for e in traced)
    errs = observe.events(org, errors=True)
    assert len(errs) == 1 and "not enough budget" in errs[0]["error"]
    last2 = observe.events(org, limit=2)
    assert len(last2) == 2 and last2[-1]["kind"] == "scheduler.exit"  # the tail of the stream
    allv = observe.events_view(org, limit=3)
    assert allv["shown"] == 3 and allv["total"] > 3
    assert "earlier one(s) not shown" in observe.render_events(allv)


def test_every_refused_tool_call_is_in_errors_with_its_text(org, clock):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "send", ok=False, error="ceo cannot message root-x: not allowed")
    log.tool(stamp(2), "ceo", "send", ok=True)
    log.emit("tool.call", stamp(3), actor="ceo", tool="read", ok=False, ms=1, error="ZeroDivisionError: x", error_type="ZeroDivisionError")
    errs = observe.events(org, errors=True)
    assert [e["error"] for e in errs] == ["ceo cannot message root-x: not allowed", "ZeroDivisionError: x"]
    assert "REFUSED" in observe.format_event(errs[0]) and "not allowed" in observe.format_event(errs[0])
    assert "FAILED" in observe.format_event(errs[1])


def test_follow_prints_only_new_lines_across_files(org):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "read")
    seen = []

    def sleeper(_):
        n = len(seen)
        if n == 0:
            log.tool(stamp(2), "ceo", "write")  # appended to an existing file
        elif n == 1:
            log.emit("run.start", stamp(3), proc="scheduler", pid=99, run="a@b", agent="a", batch=[], traces=[])  # a new file
            log.partial_line("mcp", 4242, "2026-10-18", '{"v": 1, "ts"')  # incomplete: not yielded

    gen = observe.follow_events(org, poll=0, sleep=sleeper, max_polls=4)
    for ev in gen:
        seen.append(ev["kind"])
    assert seen == ["tool.call", "run.start"] and "read" not in str(seen)


def test_follow_filters(org):
    log = EventLog(org)
    out = []

    def sleeper(_):
        log.tool(stamp(1), "ceo", "read")
        log.tool(stamp(2), "ceo", "write", ok=False, error="no")

    for ev in observe.follow_events(org, errors=True, poll=0, sleep=sleeper, max_polls=3):
        out.append(ev["tool"])
    assert out == ["write", "write"]  # one per poll; the successful reads are filtered out


# ------------------------------------------------------------------------------------------------ trace


def test_trace_lists_every_message_run_call_and_refusal(org, story):
    tr = observe.trace(org, story.task.id, now=NOW)
    kinds = [(i["kind"], i.get("type") or i.get("agent")) for i in tr["items"]]
    assert [i["id"] for i in tr["items"] if i["kind"] == "message"] == story.ids
    runs = [i for i in tr["items"] if i["kind"] == "run"]
    assert [r["run"] for r in runs] == [story.run1, story.run2, story.run3]
    assert [r["outcome"] for r in runs] == ["ok"] * 3 and tr["state"] == "done" and not tr["partial"]
    assert runs[0]["tool_calls"]["total"] == 3 and runs[0]["tool_calls"]["by_tool"] == {"inbox": 1, "delegate": 2}
    (refusal,) = runs[0]["tool_calls"]["refused"]
    assert refusal["tool"] == "delegate" and "not enough budget" in refusal["error"]
    t = tr["totals"]
    assert t["runs"] == 3 and t["run_ms"] == 87_000
    assert t["tool_calls"] == 7 and t["refusals"] == 1  # six in runs + root's delegate on the trace
    assert t["wall_ms"] == pytest.approx(125_000, abs=50) and t["user_wait_ms"] == 0
    assert t["queue_ms"] == pytest.approx(3000 + 50_000 + 20_000, abs=100)
    assert t["budget_given"] == 6 and t["budget_used"] == 3 and t["budget_returned"] == story.res.budget > 0
    assert kinds[0] == ("message", "task")
    # items are in time order
    times = [i["rel_ms"] for i in tr["items"]]
    assert times == sorted(times)


def test_trace_text_is_readable(org, story):
    text = observe.render_trace(observe.trace(org, story.task.id, now=NOW))
    lines = text.splitlines()
    assert lines[0].startswith(f'trace {story.task.id} "Ship it" -> ceo: done')
    body = "\n".join(lines)
    assert "+0s" in body and "+1m10s" in body  # relative times; eng's run starts at t=70
    assert re.search(r"root -> ceo task \"Ship it\" \+6 run\(s\)", body)
    # indented by agent depth: ceo's items 2 spaces deeper than root's, eng's 4
    eng = next(line for line in lines if f"run {story.run2.split('@')[1]}" in line)
    ceo = next(line for line in lines if f"run {story.run1.split('@')[1]}" in line)
    root = next(line for line in lines if "root -> ceo task" in line)

    def indent(line):
        return len(re.match(r"\s*\+\S+  ( *)", line).group(1))

    assert indent(root) == 0 and indent(ceo) == 2 and indent(eng) == 4
    assert "! delegate: not enough budget" in body  # the refusal with its error text
    assert re.search(r"queued 3\.0s", body) and "ran 42s" in body and "3 call(s) [delegate" in body
    assert lines[-1].startswith("totals: wall 2m05s | runs 3 (budget given 6")
    assert "waiting on you 0s" in lines[-1] and "tool calls 7 (1 refused)" in lines[-1]


def test_trace_derived_from_messages_matches_the_recorded_one(org, clock):
    story = Story(org, clock, events=True, record=False)  # old org: no `trace` frontmatter
    tr = observe.trace(org, story.task.id, now=NOW)
    assert [i["id"] for i in tr["items"] if i["kind"] == "message"] == story.ids
    assert tr["partial"] and any("derived" in n for n in tr["notes"])
    sources = {i["trace_source"] for i in tr["items"] if i["kind"] == "message"}
    assert sources <= {"derived:new", "derived:link", "derived:open-task", "derived:batch"} and "derived:new" in sources
    assert "~" in observe.render_trace(tr)
    # and the same totals as the recorded story
    assert tr["totals"]["runs"] == 3 and tr["totals"]["run_ms"] == 87_000


def test_trace_without_any_events_works_from_files_and_says_partial(org, clock):
    story = Story(org, clock, events=False, record=False)
    tr = observe.trace(org, story.task.id, now=NOW)
    assert tr["partial"] and any("no run events" in n for n in tr["notes"])
    runs = [i for i in tr["items"] if i["kind"] == "run"]
    assert len(runs) == 3 and all(r["source"] == "log" and r["queue_ms"] is None for r in runs)
    assert [r["duration_ms"] for r in runs] == [42_000, 30_000, 15_000] and tr["state"] == "done"
    text = observe.render_trace(tr)
    assert "[partial]" in text and "note: partial: no run events" in text


def test_trace_accepts_a_message_of_the_request_and_rejects_unknown_ids(org, story):
    tr = observe.trace(org, story.sub.id, now=NOW)
    assert tr["task"] == story.task.id and any("belongs to the request" in n for n in tr["notes"])
    with pytest.raises(OrgError, match="no message nope"):
        observe.trace(org, "nope")


def test_trace_open_request_with_a_crashed_run_shows_the_cause(org, clock):
    log = EventLog(org)
    clock.at(0)
    task = org.delegate(ROOT, "ceo", "Ship it", "g", "a", budget=4)
    clock.at(2)
    batch = [m.id for m in org.begin_run("ceo")]
    p = org.start_run_log("ceo")
    clock.at(60)
    org.end_run("ceo", False)
    p.write_text("# killed after 1800s timeout\n# exit -9 after 1800s\n")
    log.run("ceo", p.stem, stamp(2), 1800, batch, [task.id], ok=False, timed_out=True, killed=True, error="timed out after 1800s")
    tr = observe.trace(org, task.id, now=stamp(3000))
    (run,) = [i for i in tr["items"] if i["kind"] == "run"]
    assert run["outcome"] == "timeout" and "timed out" in run["error"] and tr["state"] == "open"
    assert "timeout" in observe.render_trace(tr) and "error: timed out after 1800s" in observe.render_trace(tr)


def test_trace_counts_time_waiting_on_the_user(org, clock):
    story_clock = clock
    story_clock.at(0)
    task = org.delegate(ROOT, "ceo", "Ship it", "g", "a", budget=6)
    story_clock.at(2)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    story_clock.at(30)
    asked = org.send("ceo", ROOT, "Need a decision: which format?", title="question", reply_to=task.id)
    org.end_run("ceo", True)
    story_clock.at(330)  # root answers 5 minutes later
    answer = org.send(ROOT, "ceo", "Use PDF.", reply_to=asked.id)
    tr = observe.trace(org, task.id, now=stamp(400))
    assert tr["totals"]["user_wait_ms"] == pytest.approx(300_000, abs=100)
    assert [i["id"] for i in tr["items"] if i["kind"] == "message"] == [task.id, asked.id, answer.id]
    assert "waiting on you 5m00s" in observe.render_trace(tr)
    # an unanswered ask runs to now
    clock.at(500)
    org.send("ceo", ROOT, "Another question", title="q2", reply_to=task.id)
    tr = observe.trace(org, task.id, now=stamp(600))
    assert tr["totals"]["user_wait_ms"] == pytest.approx(300_000 + 100_000, abs=500)


def test_trace_totals_equal_progress_runs_on_a_scheduler_run_org(org):
    made = sched_org(org, tasks=2)
    for task in made:
        tr = observe.trace(org, task.id)
        line = progress(org, task.id).splitlines()[0]
        m = re.search(r"runs (\d+) of (\d+)(?: \((\d+) returned\))?", line)
        assert m, line
        assert tr["totals"]["runs"] == int(m.group(1)) and tr["totals"]["budget_given"] == int(m.group(2))
        assert tr["totals"]["budget_returned"] == int(m.group(3) or 0)
        assert tr["state"] == "done"
    # the second task's window starts where it was created: the first task's runs are not counted twice
    assert sum(observe.trace(org, t.id)["totals"]["runs"] for t in made) == org.runs_used("ceo") + org.runs_used("ceo/eng")


def test_trace_of_a_rework_stays_in_the_trace_of_its_task(org, clock):
    clock.at(0)
    task = org.delegate(ROOT, "ceo", "Write", "g", "a", budget=5)
    clock.at(10)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    done = org.report("ceo", task.id, "done", "ok")
    org.end_run("ceo", True)
    clock.at(60)
    rework = org.delegate(ROOT, "ceo", "Write again", "g2", "a2", budget=3, revises=task.id)
    tr = observe.trace(org, task.id, now=stamp(100))
    ids = [i["id"] for i in tr["items"] if i["kind"] == "message"]
    assert ids == [task.id, done.id, rework.id]
    assert [t["task"] for t in tr["totals"]["tasks"]] == [task.id, rework.id]  # the request spans the rework
    assert [t["runs"] for t in tr["totals"]["tasks"]] == [1, 0] and tr["totals"]["budget_given"] == 8
    again = observe.trace(org, rework.id, now=stamp(100))  # a rework IS the request it revises (spec section 3)
    assert again["task"] == task.id and again["partial"] == tr["partial"] and any(f"{rework.id} belongs to the request" in n for n in again["notes"])
    assert again["items"] == tr["items"]


def test_trace_of_a_rework_counts_the_runs_of_the_whole_request(org, clock):
    """progress reports each root task on its own; the request's totals are the sum of its tasks' runs."""
    clock.at(0)
    first = org.delegate(ROOT, "ceo", "Write", "g", "a", budget=5)
    clock.at(10)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.report("ceo", first.id, "done", "ok")
    org.end_run("ceo", True)
    clock.at(60)
    second = org.delegate(ROOT, "ceo", "Write again", "g2", "a2", budget=3, revises=first.id)
    clock.at(70)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.report("ceo", second.id, "done", "better")
    org.end_run("ceo", True)
    tr = observe.trace(org, first.id, now=stamp(100))
    per = {t["task"]: t["runs"] for t in tr["totals"]["tasks"]}
    for task in (first, second):
        m = re.search(r"runs (\d+) of", progress(org, task.id).splitlines()[0])
        assert per[task.id] == int(m.group(1))
    assert tr["totals"]["runs"] == sum(per.values()) == org.runs_used("ceo") and tr["state"] == "done"
    assert "tasks: " in observe.render_trace(tr)


# ------------------------------------------------------------------------------------------------ metrics


def test_metrics_percentiles_are_exact_and_counts_equal_the_files(org, clock):
    log = EventLog(org)
    durations = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for i, secs in enumerate(durations):
        clock.at(i * 1000)
        task = org.delegate(ROOT, "ceo", f"T{i}", "g", "a", budget=3)
        clock.at(i * 1000 + 2)
        batch = [m.id for m in org.begin_run("ceo")]
        p = org.start_run_log("ceo")
        org.end_run("ceo", True)
        log.run("ceo", p.stem, stamp(i * 1000 + 2), secs, batch, [task.id], ok=i != 3, error=None if i != 3 else "boom")
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(20_000))
    assert m["runs"]["total"] == 10 == len(list((org.dir("ceo") / "runs").glob("*.log")))
    assert m["runs"]["ok"] == 9 and m["runs"]["failed"] == 1
    assert m["runs"]["duration_ms"] == {"n": 10, "p50": 50_000, "p95": 100_000, "max": 100_000}
    assert m["runs"]["queue_ms"]["n"] == 10 and m["runs"]["queue_ms"]["p50"] == pytest.approx(2005, abs=50)
    assert m["budget_spent"] == 10 and m["messages"] == {"task": 10}


def test_metrics_run_counts_per_agent_equal_run_logs_in_the_window(org):
    sched_org(org, tasks=1)
    m = observe.metrics(org, since="24h", by="agent", now=None)
    rows = {r["key"]: r for r in m["by"]["rows"]}
    for agent in ("ceo", "ceo/eng"):
        in_files = len([p for p in (org.dir(agent) / "runs").glob("*.log")])
        assert rows[agent]["runs"] == in_files == org.runs_used(agent)
    assert m["runs"]["total"] == org.runs_used("ceo") + org.runs_used("ceo/eng")
    assert m["runs"]["ok"] == m["runs"]["total"] and m["events"] == 0
    assert "no events in this window" in observe.render_metrics(m)


def test_metrics_window_excludes_older_runs(org, clock):
    clock.at(0)
    org.delegate(ROOT, "ceo", "A", "g", "a", budget=5)
    org.begin_run("ceo")
    old = org.start_run_log("ceo")
    org.end_run("ceo", True)
    clock.at(7200)
    org.delegate(ROOT, "ceo", "B", "g", "a", budget=5)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.end_run("ceo", True)
    assert observe.metrics(org, since="1h", now=stamp(7300))["runs"]["total"] == 1
    assert observe.metrics(org, since="3h", now=stamp(7300))["runs"]["total"] == 2
    assert observe.metrics(org, since=stamp(-5), now=stamp(7300))["runs"]["total"] == 2
    assert old.exists()


def test_metrics_tools_refusals_and_top_refusal_messages(org, story):
    log = EventLog(org)
    for i in range(3):  # the same reason with different numbers and ids
        log.tool(stamp(150 + i), "ceo", "delegate", ok=False, ms=2 + i,
                 error=f'not enough budget: you have {i} run(s); task 20261018T10000{i}000001-root-ab1{i} "Job {i}"')
    log.tool(stamp(160), "ceo/eng", "write", ok=False, error="you may only write inside your own directory (got ceo/x.md)")
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=NOW)
    d = m["tool_calls"]["by_tool"]["delegate"]
    assert d["calls"] == 2 + 1 + 3 + 0 and d["refused"] == 4  # story: 2 delegates (+root's), one refused; plus 3 more
    assert m["tool_calls"]["refused"] == 5
    top = m["top_refusals"][0]
    assert top["count"] == 3 and top["tools"] == {"delegate": 3} and "<id>" in top["message"] and "N run(s)" in top["message"]
    assert m["top_refusals"][1]["count"] == 1
    text = observe.render_metrics(m)
    assert "top refusals:" in text and "3x not enough budget" in text
    assert d["ms"]["n"] == 6 and d["ms"]["max"] == 5


def test_metrics_by_dimensions(org, story):
    since = "2026-10-18T00:00:00Z"
    by_agent = {r["key"]: r for r in observe.metrics(org, since=since, by="agent", now=NOW)["by"]["rows"]}
    assert by_agent["ceo"]["runs"] == 2 and by_agent["ceo/eng"]["runs"] == 1 and by_agent["ceo"]["calls"] == 4
    by_tool = {r["key"]: r for r in observe.metrics(org, since=since, by="tool", now=NOW)["by"]["rows"]}
    assert by_tool["delegate"]["calls"] == 3 and by_tool["delegate"]["refused"] == 1 and by_tool["write"]["calls"] == 1
    by_trace = observe.metrics(org, since=since, by="trace", now=NOW)["by"]["rows"]
    assert {r["key"] for r in by_trace} == {story.task.id, "-"} and next(r for r in by_trace if r["key"] == story.task.id)["runs"] == 3
    assert observe.metrics(org, since=since, by="service", now=NOW)["by"]["rows"][0]["key"] == "-"
    with pytest.raises(OrgError, match="by must be"):
        observe.metrics(org, by="colour")
    assert "by agent:" in observe.render_metrics(observe.metrics(org, since=since, by="agent", now=NOW))


def test_metrics_outcomes_from_events_and_log_tails(org, clock):
    log = EventLog(org)
    for i, (kw, tail) in enumerate([
        ({}, "# exit 0 after 5s\n"),
        ({"ok": False}, "# exit 1 after 5s\n"),
        ({"ok": False, "timed_out": True, "killed": True}, "# killed after 9s timeout\n# exit -9 after 9s\n"),
        ({"ok": False, "killed": True}, "# interrupted by scheduler shutdown\n"),
    ]):
        clock.at(i * 100)
        org.delegate(ROOT, "ceo", f"T{i}", "g", "a", budget=2)
        batch = [m.id for m in org.begin_run("ceo")]
        p = org.start_run_log("ceo")
        org.end_run("ceo", True)
        p.write_text(tail)
        log.run("ceo", p.stem, stamp(i * 100), 5, batch, [], **kw)
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(1000))["runs"]
    assert (m["ok"], m["failed"], m["timeout"], m["killed"]) == (1, 1, 1, 1)
    # without events the run logs say the same
    for p in (org.root / ".runtime" / "events").rglob("*.jsonl"):
        p.unlink()
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(1000))["runs"]
    assert (m["ok"], m["failed"], m["timeout"], m["killed"]) == (1, 1, 1, 1)


def test_metrics_scheduler_stalls_pauses(org, clock):
    log = EventLog(org)
    log.emit("scheduler.start", stamp(1), proc="scheduler", pid=1, mode="daemon")
    log.emit("scheduler.start", stamp(100), proc="scheduler", pid=2, mode="daemon")
    log.emit("scheduler.error", stamp(5), proc="scheduler", pid=1, phase="stall check", error="boom")
    log.emit("scheduler.exit", stamp(50), proc="scheduler", pid=1, reason="finished: no open tasks", runs_started=2)
    log.emit("stall.nudge", stamp(6), proc="scheduler", pid=1, task="t", to="ceo", step=0)
    log.emit("agent.pause", stamp(7), proc="scheduler", pid=1, agent="ceo", reason="failures")
    log.emit("agent.failure", stamp(7), proc="scheduler", pid=1, agent="ceo", count=3)
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", now=stamp(500))
    assert m["scheduler"] == {"starts": 2, "errors": {"stall check": 1}, "exits": {"finished: no open tasks": 1}}
    assert m["stalls"] == 1 and m["pauses"] == {"total": 1, "by_reason": {"failures": 1}} and m["agent_failures"] == 1
    assert "stall check x1" in observe.render_metrics(m)


# ------------------------------------------------------------------------------------------------ now


def test_now_works_with_no_events_and_explains_the_queue(org, clock):
    v = observe.now_view(org, now=stamp(60))
    assert v["scheduler"]["state"] == "stopped" and not v["events_seen"] and v["queued"] == []
    text = observe.render_now(v)
    assert "scheduler: stopped" in text and "waiting on you: nothing" in text and "no events recorded" in text
    clock.at(10)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    v = observe.now_view(org, now=stamp(60))
    (q,) = v["queued"]
    assert q["agent"] == "ceo" and q["unread"] == 1 and q["reason"] == "scheduler is not running" and q["waiting_s"] == pytest.approx(50, abs=1)
    assert "ceo: 1 unread, oldest 50s - scheduler is not running" in observe.render_now(v)


def test_now_queue_reasons(org, clock, monkeypatch):
    monkeypatch.setattr(observe, "scheduler_state", lambda o: SchedulerState("running", 4242, "2026-10-18 10:00:00Z"))
    clock.at(0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    assert observe.now_view(org, now=stamp(5))["queued"][0]["reason"].startswith("ready")
    org.pause("ceo", "failures")
    assert observe.now_view(org, now=stamp(5))["queued"][0]["reason"] == "paused: failures"
    org.resume("ceo")
    cfg = (org.root / "ORG.md").read_text().replace("max_parallel: 3", "max_parallel: 1")
    (org.root / "ORG.md").write_text(cfg)
    clock.at(1)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.hire(ROOT, "ops", "Ops", "Ops.")
    org.delegate(ROOT, "ops", "O", "g", "a", budget=3)
    q = {x["agent"]: x for x in observe.now_view(org, now=stamp(5))["queued"]}
    assert q["ops"]["reason"] == "max_parallel (1) runs are busy"
    org.end_run("ceo", True)
    # out of budget
    org.hire(ROOT, "poor", "Poor", "Poor.")
    org.send(ROOT, "poor", "hello")
    assert {x["agent"]: x for x in observe.now_view(org, now=stamp(5))["queued"]}["poor"]["reason"] == "no budget"


def test_now_shows_scheduler_runs_in_flight_and_errors(org, story, monkeypatch):
    log = story.log
    # a live scheduler with a heartbeat and a run in flight on eng
    monkeypatch.setattr(observe, "scheduler_state", lambda o: SchedulerState("running", 7000, "2026-10-18 10:00:00Z"))
    log.emit("scheduler.heartbeat", stamp(190), proc="scheduler", pid=7000, running=["ceo/eng"], runnable=0, waiting_on_you=0)
    story.clock.at(180)
    org.delegate(ROOT, "ceo", "Another", "g", "a", budget=2)
    org.begin_run("ceo")
    p = org.start_run_log("ceo")
    org.save_ledger("running", {"ceo": {"pgid": 123, "lstart": "x", "started": stamp(181).timestamp(), "scheduler": 7000,
                                        "log": str(p.relative_to(org.root))}})
    log.tool(stamp(195), "ceo", "send", ok=False, error="ceo cannot message nobody", run=f"ceo@{p.stem}")
    log.tool(stamp(-2000), "ceo", "send", ok=False, error="an old refusal")  # outside the 15 minutes
    v = observe.now_view(org, now=stamp(200))
    s = v["scheduler"]
    assert s["state"] == "running" and s["mode"] == "until_done" and s["uptime_s"] == pytest.approx(200, abs=1)
    assert s["last_heartbeat_age_s"] == pytest.approx(10, abs=1)
    (r,) = v["runs_in_flight"]
    assert r["agent"] == "ceo" and r["run"] == f"ceo@{p.stem}" and r["elapsed_s"] == pytest.approx(19, abs=1) and r["batch"] == ["Another"]
    assert v["errors_15m"]["count"] == 2  # the refused delegate of the story (t=10) and the new send
    text = observe.render_now(v)
    assert "scheduler: running pid 7000 (until_done, up 3m20s, last heartbeat 10s ago)" in text
    assert "runs in flight 1/3:" in text and "ceo 19s Another" in text
    assert "errors in the last 15 min: 2" in text and "ceo cannot message nobody" in text and "an old refusal" not in text


def test_now_lists_what_waits_on_you(org, clock):
    clock.at(0)
    task = org.delegate(ROOT, "ceo", "Ship it", "g", "a", budget=3)
    clock.at(5)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.report("ceo", task.id, "blocked", "Need the logo file")
    org.end_run("ceo", True)
    v = observe.now_view(org, now=stamp(60))
    assert len(v["waiting_on_you"]) == 1 and "blocked result from ceo" in v["waiting_on_you"][0] and "Need the logo file" in v["waiting_on_you"][0]
    assert "waiting on you (1):" in observe.render_now(v)


def test_now_heartbeat_of_a_stopped_scheduler_reports_its_exit(org, story):
    v = observe.now_view(org, now=NOW)
    assert v["scheduler"]["state"] == "stopped" and v["scheduler"]["last_exit"] == "finished: no open tasks"
    assert "scheduler: stopped (last exit: finished: no open tasks)" in observe.render_now(v)


# ------------------------------------------------------------------------------------------------ check


def by_id(res):
    return {c["id"]: c for c in res["checks"]}


def test_check_passes_on_a_healthy_scheduler_run_org(org):
    sched_org(org, tasks=2)
    res = observe.check(org)
    assert res["ok"], observe.render_check(res)
    assert all(c["ok"] for c in res["checks"]) and len(res["checks"]) == 6
    assert "all checks passed" in observe.render_check(res)


def test_check_passes_on_the_story_with_events(org, story):
    res = observe.check(org, now=NOW)
    assert res["ok"], observe.render_check(res)
    assert "3 run.start" in by_id(res)["d"]["details"][0]


def test_check_a_missing_recipient_copy(org, story):
    path = next((org.dir("ceo/eng") / "read").glob("*.md"))
    mid = path.stem
    os.utime(next((org.dir("ceo") / "sent").glob(f"{mid}.md")), (0, 0))
    path.unlink()
    res = by_id(observe.check(org, now=NOW))
    assert not res["a"]["ok"] and any(mid in d and "has no copy" in d for d in res["a"]["details"])
    # budget no longer balances either: the grant was charged but never credited
    assert not res["b"]["ok"]


def test_check_does_not_fail_on_a_message_that_is_being_delivered(org):
    msg = Message(sender=ROOT, to="ceo", type="task", title="T", body="b", budget=3, id="20261018T100000000000-root-ab12")
    from orgmcp.core import atomic_write

    msg.created = "2026-10-18T10:00:00"
    atomic_write(org.dir(ROOT) / "sent" / f"{msg.id}.md", msg.to_text())  # the recipient copy is written a moment later
    res = observe.check(org)
    assert res["ok"], observe.render_check(res)
    assert "3 in delivery" in by_id(res)["b"]["details"][0]
    os.utime(org.dir(ROOT) / "sent" / f"{msg.id}.md", (0, 0))  # ... but not forever
    res = by_id(observe.check(org))
    assert not res["a"]["ok"] and not res["b"]["ok"]


def test_check_a_missing_sender_copy_and_unparsable_and_duplicate_ids(org, story):
    sent = org.dir("ceo") / "sent" / f"{story.sub.id}.md"
    sent_id = sent.stem
    os.utime(next(org.dir("ceo/eng").rglob(f"{sent_id}.md")), (0, 0))
    sent.unlink()
    (org.dir("ceo") / "read" / "broken.md").write_text("no frontmatter at all\n")
    dup = next((org.dir("ceo/eng") / "read").glob("*.md"))
    (org.dir("ceo/eng") / "inbox" / dup.name).write_text(dup.read_text())
    for f in org.dir("ceo/eng").rglob(f"{sent_id}.md"):
        os.utime(f, (0, 0))  # every received copy is old whatever the real clock says (NOW is a fixed 2026-10-18 instant)
    res = by_id(observe.check(org, now=NOW))["a"]
    text = "\n".join(res["details"])
    assert not res["ok"] and "has no sent copy" in text and "ceo/read/broken.md: no frontmatter" in text and "appears 2 times" in text


def test_check_budget_imbalance_names_the_difference(org, story):
    path = next((org.dir("ceo/eng") / "read").glob("*.md"))
    from orgmcp.core import join_frontmatter, split_frontmatter

    meta, body = split_frontmatter(path.read_text())
    meta["budget"] = int(meta.get("budget", 0)) + 4
    path.write_text(join_frontmatter(meta, body))
    res = by_id(observe.check(org, now=NOW))["b"]
    assert not res["ok"] and "handed down" in res["details"][0] and "appeared from nowhere" in res["details"][0]
    assert by_id(observe.check(org, now=NOW))["a"]["ok"]  # both copies still parse: only the arithmetic is off


def test_check_budget_holds_after_retire_reclaim_and_returns(org, clock):
    clock.at(0)
    org.hire("ceo", "qa", "QA", "Test.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=9)
    clock.at(1)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    sub = org.delegate("ceo", "ceo/eng", "E", "g", "a", budget=3)
    org.send("ceo", "ceo/qa", "standby", budget=3, wake=False)
    org.end_run("ceo", True)
    clock.at(2)
    org.begin_run("ceo/eng")
    org.start_run_log("ceo/eng")
    org.report("ceo/eng", sub.id, "done", "ok")  # returns eng's unspent runs with the result
    org.end_run("ceo/eng", True)
    assert observe.check(org, now=stamp(60))["ok"], observe.render_check(observe.check(org, now=stamp(60)))
    org.reclaim("ceo", "qa", 1)
    assert observe.check(org, now=stamp(60))["ok"]
    org.retire("ceo", "qa", "done")  # nested: its 2 unspent runs are refunded to ceo by a runtime note
    res = observe.check(org, now=stamp(60))
    assert res["ok"], observe.render_check(res)
    org.hire(ROOT, "ops", "Ops", "Ops.")
    org.send(ROOT, "ops", "go", budget=5)
    org.begin_run("ops")
    org.start_run_log("ops")
    org.end_run("ops", True)
    assert observe.check(org, now=stamp(60))["ok"]
    org.retire(ROOT, "ops", "gone")  # top level: its unspent runs are dropped (root has no limit)
    res = observe.check(org, now=stamp(60))
    assert res["ok"], observe.render_check(res)
    assert "dropped 4" in by_id(res)["b"]["details"][0]


def test_check_stuck_inflight_without_a_live_run(org, clock):
    clock.at(0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")  # a batch taken, then the scheduler died
    org.start_run_log("ceo")
    old = stamp(-600).timestamp()
    for p in (org.dir("ceo") / "inflight").glob("*.md"):
        os.utime(p, (old, old))
    res = by_id(observe.check(org, now=stamp(10)))["c"]
    assert not res["ok"] and "ceo: 1 message(s) inflight" in res["details"][0] and "no scheduler is running" in res["details"][0]


def test_check_inflight_with_a_live_recorded_process_passes(org, clock, monkeypatch):
    clock.at(0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")
    p = org.start_run_log("ceo")
    old = stamp(-600).timestamp()
    for f in (org.dir("ceo") / "inflight").glob("*.md"):
        os.utime(f, (old, old))
    org.save_ledger("running", {"ceo": {"pgid": 99999, "lstart": "x", "started": 0, "scheduler": 1, "log": str(p.relative_to(org.root))}})
    monkeypatch.setattr(observe, "judge_orphan", lambda rec: "ours")
    assert by_id(observe.check(org, now=stamp(10)))["c"]["ok"]
    monkeypatch.setattr(observe, "judge_orphan", lambda rec: "gone")
    assert not by_id(observe.check(org, now=stamp(10)))["c"]["ok"]


def test_check_run_start_without_end_and_without_a_live_process(org, story):
    story.log.emit("run.start", stamp(150), proc="scheduler", pid=7000, run="ceo@20261018T100230000000", agent="ceo",
                   batch=[], traces=[], pgid=1)
    res = by_id(observe.check(org, now=NOW))["d"]
    assert not res["ok"] and "ceo@20261018T100230000000: run.start" in res["details"][0] and "no run.end" in res["details"][0]


def test_check_run_log_without_run_start(org, story):
    clock = story.clock
    clock.at(160)
    org.delegate(ROOT, "ceo", "More", "g", "a", budget=2)
    org.begin_run("ceo")
    p = org.start_run_log("ceo")
    org.end_run("ceo", True)
    res = by_id(observe.check(org, now=NOW))["d"]
    assert not res["ok"] and f"ceo@{p.stem}: run log without a run.start" in res["details"][0]
    p.write_text("# failed to start: kiro-cli missing\n")  # a run that never started has no run.start by design
    assert by_id(observe.check(org, now=NOW))["d"]["ok"]


def test_check_run_events_are_ignored_for_runs_before_events_began(org, clock):
    clock.at(0)
    org.delegate(ROOT, "ceo", "Old", "g", "a", budget=2)
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.end_run("ceo", True)
    EventLog(org).emit("scheduler.start", stamp(100), proc="scheduler", pid=1, mode="daemon")
    assert by_id(observe.check(org, now=stamp(200)))["d"]["ok"]


def test_check_seq_gap(org):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "read")
    log.tool(stamp(2), "ceo", "read")
    assert by_id(observe.check(org, now=NOW))["e"]["ok"]
    log.emit("tool.call", stamp(3), actor="ceo", tool="read", ok=True, ms=1, skip_seq=2)
    res = by_id(observe.check(org, now=NOW))["e"]
    assert not res["ok"] and "seq jumps from 2 to 5 (2 line(s) lost)" in res["details"][0]


def test_check_seq_restarts_at_one_in_each_days_file(org):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "read")
    log.tool(stamp(2), "ceo", "read")
    log.tool(stamp(86400 + 1), "ceo", "read")  # the same process, next day: a new file, seq restarts at 1
    assert by_id(observe.check(org, now=NOW))["e"]["ok"]
    log.tool(stamp(86400 + 2), "ceo", "read")
    assert by_id(observe.check(org, now=NOW))["e"]["ok"]
    log.emit("tool.call", stamp(86400 + 3), actor="ceo", tool="read", ok=True, ms=1, skip_seq=1)  # one line lost on day 2
    res = by_id(observe.check(org, now=NOW))["e"]
    assert not res["ok"] and "seq jumps from 2 to 4" in res["details"][0] and res["details"][0].startswith("2026-10-19/")
    other = EventLog(org)
    other.started[("mcp", 9)] = int(T0.timestamp() * 1000)
    other.emit("tool.call", stamp(5), pid=9, actor="ceo", tool="read", ok=True, ms=1, skip_seq=3)  # its first line has seq 4
    res = by_id(observe.check(org, now=NOW))["e"]
    assert not res["ok"] and "first seq is 4, expected 1" in res["details"][0]


def test_check_stale_pid_file(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "scheduler.pid").write_text("999999")
    res = by_id(observe.check(org))["f"]
    assert not res["ok"] and "stale" in res["details"][0]
    (org.root / ".runtime" / "scheduler.pid").unlink()
    assert by_id(observe.check(org))["f"]["ok"]


def test_check_pid_file_of_a_foreign_process_is_not_trusted(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "scheduler.pid").write_text(str(os.getpid()))  # alive, but not a scheduler of this org
    res = by_id(observe.check(org))["f"]
    assert not res["ok"] and "not verified" in res["details"][0]


def test_check_is_read_only(org, story):
    def snapshot():
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in org.root.rglob("*") if p.is_file() and ".git/" not in str(p))

    before = snapshot()
    for view in ("now", "trace", "metrics", "events", "check"):
        observe.observe_text(org, view, story.task.id if view == "trace" else None, since="2026-10-18T00:00:00Z", now=NOW)
    assert snapshot() == before


# ------------------------------------------------------------------------------------------------ surfaces


def test_observe_text_dispatch_and_caps(org, story):
    assert observe.observe_text(org, "check", now=NOW).endswith("all checks passed")
    assert "runs 3" in observe.observe_text(org, "trace", story.task.id, now=NOW)
    assert observe.observe_text(org, "metrics", since="2026-10-18T00:00:00Z", now=NOW).startswith("metrics ")
    with pytest.raises(OrgError, match="trace needs target"):
        observe.observe_text(org, "trace")
    with pytest.raises(OrgError, match="view must be one of"):
        observe.observe_text(org, "weather")
    # events: target is a trace id, an agent or a kind
    since = "2026-10-18T00:00:00Z"
    by_trace = observe.observe_text(org, "events", story.task.id, since=since, now=NOW)
    by_agent = observe.observe_text(org, "events", "ceo/eng", since=since, now=NOW)
    by_kind = observe.observe_text(org, "events", "scheduler", since=since, now=NOW)
    assert "tool.call" in by_trace and "scheduler.start" in by_kind and "ceo/eng" in by_agent and "scheduler.start" not in by_agent
    assert "not enough budget" in observe.observe_text(org, "events", since=since, errors_only=True, now=NOW)
    capped = observe.observe_text(org, "trace", story.task.id, now=NOW, max_lines=3)
    assert "more line(s), narrow with" in capped


def test_trace_text_cap_says_how_to_narrow(org, story):
    text = observe.render_trace(observe.trace(org, story.task.id, now=NOW), max_lines=4)
    assert re.search(r"\.\.\. \d+ more line\(s\), narrow with observe events --trace", text)


def test_cli_views_and_json(org, story, capsys, monkeypatch):
    root = str(org.root)
    monkeypatch.setattr("orgmcp.core.utcnow", lambda: NOW)  # the command line opens its own Org: the clock of its runtime is the patch point
    main(["--root", root, "obs", "trace", story.task.id])
    assert "totals: wall" in capsys.readouterr().out
    main(["--root", root, "obs", "trace", story.task.id, "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["totals"]["runs"] == 3 and data["task"] == story.task.id
    main(["--root", root, "obs", "metrics", "--since", "2026-10-18T00:00:00Z", "--by", "agent", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["runs"]["total"] == 3 and out["by"]["dimension"] == "agent"
    main(["--root", root, "obs", "events", "--since", "2026-10-18T00:00:00Z", "--errors", "--json"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["tool"] == "delegate"
    main(["--root", root, "obs", "events", "--since", "2026-10-18T00:00:00Z", "--kind", "run.end", "--limit", "2"])
    assert "2 of 3 matching event(s)" in capsys.readouterr().out
    main(["--root", root, "obs", "now"])
    assert "scheduler:" in capsys.readouterr().out
    main(["--root", root, "obs", "now", "--json"])
    assert json.loads(capsys.readouterr().out)["scheduler"]["state"] == "stopped"
    main(["--root", root, "check", "--json"])
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_cli_check_exits_1_on_a_failure(org, capsys):
    (org.root / ".runtime" / "scheduler.pid").write_text("999999")
    with pytest.raises(SystemExit) as exc:
        main(["--root", str(org.root), "check"])
    assert exc.value.code == 1 and "FAIL" in capsys.readouterr().out


def test_cli_errors_are_plain_messages(org, capsys):
    with pytest.raises(SystemExit):
        main(["--root", str(org.root), "obs", "trace", "nope"])
    assert "error: no message nope" in capsys.readouterr().err


def test_cli_watch_and_follow_exit_cleanly_on_ctrl_c(org, story, capsys, monkeypatch):
    def interrupt(_):
        raise KeyboardInterrupt

    monkeypatch.setattr("orgmcp.cli_obs.time.sleep", interrupt)
    main(["--root", str(org.root), "obs", "now", "--watch", "5"])
    assert "scheduler:" in capsys.readouterr().out
    main(["--root", str(org.root), "obs", "events", "--since", "2026-10-18T00:00:00Z", "--limit", "1", "--follow"])
    assert "matching event" in capsys.readouterr().out


def test_cli_follow_prints_new_events(org, capsys, monkeypatch):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "read")
    calls = []

    def sleeper(_):
        if not calls:
            calls.append(1)
            log.tool(stamp(2), "ceo", "write")
        else:
            raise KeyboardInterrupt

    monkeypatch.setattr("orgmcp.cli_obs.time.sleep", sleeper)
    main(["--root", str(org.root), "obs", "events", "--since", "2026-10-01T00:00:00Z", "--follow"])
    out = capsys.readouterr().out
    assert "tool.call read" in out and "tool.call write" in out


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def test_observe_tool_is_root_only_and_read_only(org, story):
    org.runtime = dataclasses.replace(org.runtime, clock=FakeClock(NOW))
    root = build_server(org, ROOT)
    names = {t.name for t in asyncio.run(root.list_tools())}
    assert "observe" in names
    assert "observe" not in {t.name for t in asyncio.run(build_server(org, "ceo").list_tools())}
    assert "observe" not in {t.name for t in asyncio.run(build_server(org, "ceo/eng").list_tools())}
    assert "scheduler:" in call(root, "observe")
    assert "totals: wall" in call(root, "observe", view="trace", target=story.task.id)
    assert "all checks passed" in call(root, "observe", view="check")
    assert "tool.call" in call(root, "observe", view="events", target="ceo", since="2026-10-18T00:00:00Z", limit=5)
    assert call(root, "observe", view="metrics", since="2026-10-18T00:00:00Z", by="tool").count("by tool:") == 1
    with pytest.raises(Exception, match="trace needs target"):
        call(root, "observe", view="trace")


def test_observe_tool_docstring_is_short_and_says_read_only():
    from orgmcp import observe as o

    class Fake:
        tools = {}

        def tool(self):
            def deco(fn):
                Fake.tools[fn.__name__] = fn
                return fn

            return deco

    o.register_observe_tool(Fake(), None)
    doc = Fake.tools["observe"].__doc__
    assert doc.startswith("Read-only") and len(doc) < 900
    for view in ("now", "trace", "metrics", "events", "check"):
        assert view in doc


def test_stamp_trace_helper_roundtrips_through_the_loader(org, clock):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    stamp_trace(org, task.id, task.id)
    loaded = Message.load(next((org.dir("ceo") / "inbox").glob("*.md")))
    assert loaded.id == task.id  # the core loader ignores the unknown key
    assert observe.build_messages(observe.scan_messages(org))[task.id].trace == task.id


def test_run_ids_helper(org, clock):
    clock.at(0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    org.begin_run("ceo")
    p = org.start_run_log("ceo")
    assert run_ids(org, "ceo") == [f"ceo@{p.stem}"]


def test_runs_of_agents_that_no_longer_exist_are_known_from_events(org, clock):
    log = EventLog(org)
    log.run("gone/agent", "20261018T100100000000", stamp(60), 12, ["20261018T100000000000-root-ab12"], [], pid=1)
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", by="agent", now=stamp(500))
    assert m["runs"]["total"] == 1 and m["by"]["rows"][0]["key"] == "gone/agent"
    assert m["runs"]["duration_ms"]["p50"] == 12_000 and m["runs"]["queue_ms"]["p50"] == pytest.approx(60_005, abs=10)


def test_the_skill_sends_the_assistant_to_observe_instead_of_guessing():
    from orgmcp.skill import skill_source

    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125
    for needle in ("why something failed or took long, or what it cost", "use `observe` (read-only), never guesses",
                   '`view="trace"` with\n  the task id', '"now"', '"metrics"', "`errors_only=True`"):
        assert needle in skill, needle
