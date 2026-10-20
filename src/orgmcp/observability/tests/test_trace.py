# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import re
import sys
import time

import pytest
import testkit
from testkit import observability_world as observe
from testkit.reach.orgmcp.core import ROOT, Org, OrgError
from testkit.reach.orgmcp.progress import progress
from testkit.health_world import Scheduler
from testkit.obs_fixtures import EventLog, Story, stamp
from testkit.observability_world import freeze

FAKE = str(testkit.FAKE_AGENT)
NOW = stamp(200)


@pytest.fixture
def org(tmp_path):
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/testkit/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(org):
    return freeze(org)


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


def test_trace_text_cap_says_how_to_narrow(org, story):
    text = observe.render_trace(observe.trace(org, story.task.id, now=NOW), max_lines=4)
    assert re.search(r"\.\.\. \d+ more line\(s\), narrow with observe events --trace", text)
