# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit import observability_world as observe
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.obs_fixtures import Story, stamp
from testkit.observability_world import freeze, scheduler_is

from hirearchy.daemon import SchedulerState

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


def test_now_queue_reasons(org, clock, process_overrides):
    scheduler_is(process_overrides, SchedulerState("running", 4242, "2026-10-18 10:00:00Z"), org)
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


def test_now_shows_scheduler_runs_in_flight_and_errors(org, story, process_overrides):
    log = story.log
    # a live scheduler with a heartbeat and a run in flight on eng
    scheduler_is(process_overrides, SchedulerState("running", 7000, "2026-10-18 10:00:00Z"), org)
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
