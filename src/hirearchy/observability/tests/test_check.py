# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import sys
import time

import pytest
import testkit
from testkit import observability_world as observe
from testkit.health_world import Scheduler, with_ports
from testkit.reach.hirearchy.core import ROOT, Message, Org
from testkit.obs_fixtures import T0, EventLog, Story, stamp
from testkit.observability_world import freeze

from hirearchy.processes import OrphanJudge
from hirearchy.processes.testing import fake_world

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
    from testkit.reach.hirearchy.core import atomic_write

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
    from testkit.reach.hirearchy.core import join_frontmatter, split_frontmatter

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


def test_check_inflight_with_a_live_recorded_process_passes(org, clock, monkeypatch, tmp_path):
    clock.at(0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")
    p = org.start_run_log("ceo")
    old = stamp(-600).timestamp()
    for f in (org.dir("ceo") / "inflight").glob("*.md"):
        os.utime(f, (old, old))
    org.save_ledger("running", {"ceo": {"pgid": 99999, "lstart": "x", "started": 0, "scheduler": 1, "log": str(p.relative_to(org.root))}})
    world = fake_world(tmp_path)  # the process 99999 of the record is a session leader that started at "x": ours; then it is gone
    table = world.spawner
    table.add(99999, started="x")
    with_ports(org, {OrphanJudge: world.judge})
    assert by_id(observe.check(org, now=stamp(10)))["c"]["ok"]
    table.exit(99999)
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
