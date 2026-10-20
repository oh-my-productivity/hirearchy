# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import sys
import time
from datetime import timedelta

import pytest
from testkit.health_world import Scheduler, agent_health
from testkit.legacy.orgmcp.core import ROOT, Org, join_frontmatter, split_frontmatter, utcnow
from testkit.review_world import REVIEW_ACTIONS, review, review_if_due, total_runs

from orgmcp.health.api import FLAGS

ENG = "ceo/eng"


def now():
    """Late enough that freshly hired agents count as idle when `idle_after_seconds` is tiny."""
    return utcnow() + timedelta(hours=1)


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def flag_idle(org):
    configure(org, health={"idle_after_seconds": -1})


def fund(org, addr="ceo", budget=10):
    """Give an agent budget and let it read the mail, so only `idle` can flag it."""
    org.send(ROOT, addr, "budget", budget=budget)
    org.begin_run(addr)
    org.end_run(addr, ok=True)


def add_runs(org, addr, n):
    """Fake run logs (each one is a used run) with unique names."""
    d = org.dir(addr) / "runs"
    start = len(list(d.glob("*.log")))
    for i in range(n):
        (d / f"20260101T000000{start + i:06d}.log").touch()


def runtime_notes(org, addr):
    return [m for m in org.received(addr) if m.sender == "runtime" and m.title.startswith("health review")]


def snapshot(org):
    # the event log (.runtime/events) records even a dry run, so it is not part of the organization's content
    return {p: p.read_bytes() for p in org.root.rglob("*") if p.is_file() and ".git" not in p.parts and "events" not in p.parts}


# ------------------------------------------------------------------ who hears what
def test_healthy_org_sends_nothing_but_updates_the_ledger(org):
    fund(org)
    result = review(org, now())
    assert result.notes == [] and result.flagged == 0
    assert all(not runtime_notes(org, a) for a in (ROOT, "ceo", ENG))
    assert org.ledger("reviews")["notified"] == {} and org.ledger("reviews")["runs"] == 0


def test_org_without_agents_only_updates_the_ledger(tmp_path):
    empty = Org.init(tmp_path / "empty", "m")
    assert review(empty, now()).notes == []
    assert set(empty.ledger("reviews")) == {"at", "runs", "notified"} and runtime_notes(empty, ROOT) == []


def test_manager_gets_one_compact_note_with_reasons_and_actions(org):
    flag_idle(org)
    fund(org)
    result = review(org, now())
    (note,) = runtime_notes(org, "ceo")
    assert note.title == "health review: 1 new problem(s)"
    assert "`ceo/eng` idle: no open tasks and no activity" in note.body
    assert REVIEW_ACTIONS["idle"].format(a=ENG) in note.body
    assert "ceo/MEMORY.md" in note.body
    assert runtime_notes(org, ENG) == []  # a worker with no team is nobody's manager
    assert result.notified["ceo"] == [f"{ENG}:idle"]


def test_every_flag_has_an_action():
    assert set(REVIEW_ACTIONS) == set(FLAGS)
    for flag in FLAGS:
        assert ENG in REVIEW_ACTIONS[flag].format(a=ENG)


def test_only_new_pairs_are_sent_and_persistent_ones_are_not_repeated(org):
    flag_idle(org)
    fund(org)
    review(org, now())
    for _ in range(3):  # the same problem, review after review: the pair must stay "known"
        review(org, now())
    assert len(runtime_notes(org, "ceo")) == 1 and len(runtime_notes(org, ROOT)) == 4

    org.hire("ceo", "ops", "Operations", "Operate.")
    review(org, now())
    assert len(runtime_notes(org, "ceo")) == 2
    newest = runtime_notes(org, "ceo")[-1]
    assert "`ceo/ops` idle" in newest.body and "`ceo/eng`" not in newest.body


def test_a_problem_that_goes_away_and_returns_is_new_again(org):
    flag_idle(org)
    fund(org)
    review(org, now())
    configure(org, health={"idle_after_seconds": 10**9})  # eng is no longer idle
    review(org, now())
    flag_idle(org)
    review(org, now())
    assert len(runtime_notes(org, "ceo")) == 2


def test_paused_manager_is_skipped_but_stays_in_root_summary(org):
    flag_idle(org)
    fund(org)
    org.pause("ceo", "failures")
    result = review(org, now())
    assert runtime_notes(org, "ceo") == [] and result.skipped == {"ceo": "paused"}
    (summary,) = runtime_notes(org, ROOT)
    assert "`ceo` paused" in summary.body and "`ceo/eng` idle" in summary.body
    assert "Managers not notified: `ceo` (paused)" in summary.body
    org.resume("ceo")  # it was never told, so it hears about eng as soon as it can act
    review(org, now())
    assert len(runtime_notes(org, "ceo")) == 1


def test_manager_without_budget_is_skipped(org):
    flag_idle(org)  # ceo has no budget at all
    result = review(org, now())
    assert result.skipped == {"ceo": "no budget left"} and runtime_notes(org, "ceo") == []
    assert "`ceo/eng` idle" in runtime_notes(org, ROOT)[0].body


def test_root_summary_lists_every_flagged_agent_every_review(org):
    flag_idle(org)
    fund(org)
    review(org, now())
    org.begin_run("ceo")  # ceo reads its review note (unread mail would make it "not idle")
    org.end_run("ceo", ok=True)
    review(org, now())
    first, second = runtime_notes(org, ROOT)
    assert first.title == "health review: 2 of 2 agents flagged" and first.body == second.body
    assert first.body.startswith("Health review: 2 agents, 2 flagged.")
    assert "- `ceo` idle:" in first.body and "- `ceo/eng` idle:" in first.body
    assert REVIEW_ACTIONS["idle"].format(a="ceo") in first.body  # root's direct report: suggested action
    assert REVIEW_ACTIONS["idle"].format(a=ENG) not in first.body  # not root's to act on
    assert org.ledger("reviews")["notified"][ROOT] == ["ceo:idle", f"{ENG}:idle"]


def test_a_team_problem_is_reported_to_the_manager_of_the_team_lead(org):
    org.hire("ceo", "cto", "CTO", "Lead tech.", can_hire=True)
    org.hire("ceo/cto", "dev", "Developer", "Code.")
    configure(org, health={"stranded_after_seconds": 10**9})  # funded and quiet is not what this test is about
    fund(org)
    fund(org, "ceo/cto")
    org.pause("ceo/cto/dev", "failures")
    result = review(org, now())
    (note,) = runtime_notes(org, "ceo")
    assert "`ceo/cto` team: `ceo/cto/dev` is paused" in note.body and "ask `ceo/cto`" in note.body
    assert result.notified["ceo"] == ["ceo/cto:branch:paused"]
    assert runtime_notes(org, "ceo/cto")[0].body.count("`ceo/cto/dev` paused") == 1  # the lead hears it directly


def test_runtime_notes_are_not_tasks_rework_or_quality_problems(org):
    for i in range(4):
        task = org.delegate(ROOT, ENG, f"Job {i}", "g", "a", budget=2)
        org.report(ENG, task.id, "done", "ok")
    for _ in range(4):  # review notes and stall reminders
        org.notify(ENG, "health review: 1 new problem(s)", "x")
        org.notify(ENG, "reminder: Job", "y")
    h = agent_health(org, ENG, now())
    assert (h.tasks_received, h.rework, h.failed, h.blocked) == (4, 0, 0, 0)
    assert "low_quality" not in h.flags


# ------------------------------------------------------------------ dry run
def test_dry_run_reports_but_writes_nothing(org):
    flag_idle(org)
    fund(org)
    before = snapshot(org)
    result = review(org, now(), dry_run=True)
    assert [n.to for n in result.notes] == ["ceo", ROOT]
    assert snapshot(org) == before and not (org.root / ".runtime/reviews.json").exists()
    assert result.render(dry_run=True).startswith("2 flagged agent(s); would send 2 note(s)")


# ------------------------------------------------------------------ cadence
def test_first_check_only_starts_the_clock(org):
    assert review_if_due(org, now()) is None
    assert org.ledger("reviews")["runs"] == 0


def test_review_is_due_after_review_every_runs(org):
    flag_idle(org)
    fund(org)
    configure(org, review_every_runs=5)
    t = utcnow()
    review_if_due(org, t)  # baseline
    add_runs(org, "ceo", 4)
    assert review_if_due(org, t) is None
    add_runs(org, ENG, 1)  # counted across the whole organization
    assert total_runs(org) == 5
    assert review_if_due(org, now()) is not None
    assert org.ledger("reviews")["runs"] == 5
    assert review_if_due(org, t) is None  # counts from the last review
    add_runs(org, "ceo", 5)
    assert review_if_due(org, t) is not None


def test_review_is_due_after_review_every_seconds(org):
    configure(org, review_every_seconds=100, review_every_runs=1000)
    t0 = utcnow()
    review_if_due(org, t0)
    assert review_if_due(org, t0 + timedelta(seconds=99)) is None
    assert review_if_due(org, t0 + timedelta(seconds=100)) is not None
    assert review_if_due(org, t0 + timedelta(seconds=150)) is None  # the clock restarted with that review


def test_cadence_comes_from_files_not_memory(org):
    configure(org, review_every_runs=3, review_every_seconds=10**9)
    review_if_due(org, utcnow())
    add_runs(org, "ceo", 2)
    assert review_if_due(org, utcnow()) is None
    add_runs(org, "ceo", 1)  # "after a restart": only the ledger and the run logs carry state
    assert review_if_due(Org(org.root), utcnow()) is not None


# ------------------------------------------------------------------ scheduler
class Clock:
    """A fixed starting time plus an offset, so a test can move time forward without sleeping, and the wall clock (a loaded machine) cannot move it."""

    def __init__(self):
        self.base = time.time()
        self.offset = 0.0

    def __call__(self):
        return self.base + self.offset


def no_agent(org, addr, prompt):
    """The run of an agent woken by a review note: a process that does nothing (never the real kiro-cli)."""
    return [sys.executable, "-c", "pass"], org.dir(addr), {**os.environ}


SCHEDULERS = []


@pytest.fixture(autouse=True)
def settled():
    """Let the runs a test's schedulers started end and be reaped, so no process and no run log is left open."""
    yield
    for sched in SCHEDULERS:
        for _ in range(500):
            if not sched.runs:
                break
            time.sleep(0.02)
            sched.reap()
    SCHEDULERS.clear()


def scheduler(org, clock):
    sched = Scheduler(org, no_agent, echo=lambda _: None, clock=clock)  # a review note wakes its manager: that run does nothing
    SCHEDULERS.append(sched)
    return sched


def test_tick_reviews_when_the_time_is_up_and_not_before(org):
    flag_idle(org)
    fund(org)
    configure(org, review_every_seconds=1000, review_every_runs=1000)
    clock = Clock()
    sched = scheduler(org, clock)
    sched.tick()  # starts the review clock
    assert org.ledger("reviews") and runtime_notes(org, ROOT) == []
    clock.offset = 999
    sched.tick()
    assert runtime_notes(org, ROOT) == []
    clock.offset = 3601  # idle needs the agents to be an hour old (idle_after_seconds is tiny)
    sched.tick()
    assert len(runtime_notes(org, ROOT)) == 1 and len(runtime_notes(org, "ceo")) == 1
    sched.tick()
    assert len(runtime_notes(org, ROOT)) == 1  # not due again


def test_tick_reviews_after_enough_runs_and_a_restart_does_not_reset_the_count(org):
    flag_idle(org)
    fund(org)
    configure(org, review_every_runs=3, review_every_seconds=10**9)
    clock = Clock()
    scheduler(org, clock).tick()
    add_runs(org, "ceo", 2)
    scheduler(org, clock).tick()  # a new scheduler (restart) sees the same two runs
    assert runtime_notes(org, ROOT) == []
    add_runs(org, ENG, 1)
    scheduler(org, clock).tick()
    assert len(runtime_notes(org, ROOT)) == 1 and org.ledger("reviews")["runs"] == 3


def test_tick_on_a_healthy_org_costs_nothing(org):
    fund(org)
    configure(org, review_every_seconds=10)
    clock = Clock()
    sched = scheduler(org, clock)
    sched.tick()
    clock.offset = 11
    sched.tick()
    assert all(not runtime_notes(org, a) for a in (ROOT, "ceo", ENG))
    assert org.ledger("reviews")["notified"] == {}
