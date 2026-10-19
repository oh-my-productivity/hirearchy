"""`progress`: waiting on blocked tasks whose team can still run, "Needs you", and run counts per root task."""

import pytest

from orgmcp.app import wire_attention
from orgmcp.core import ROOT
from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.progress import describe_progress, progress, work_in_flight
from orgmcp.progress._reporter import DerivedProgressReporter
from orgmcp.progress.testing import FixedSnapshots, SpyProgressView

ENG = "ceo/eng"


class Clock:
    """A fake clock whose ``sleep`` advances time and can run an action at the n-th sleep."""

    def __init__(self, actions=None):
        self.now, self.sleeps, self.actions = 0.0, 0, actions or {}

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps += 1
        self.now += seconds
        action = self.actions.get(self.sleeps)
        if action:
            action()


def waiting(org, clock, wait=60, poll=2.0, task_id=None):
    return progress(org, task_id, wait_seconds=wait, poll=poll, sleep=clock.sleep, clock=clock)


def run(org, addr):
    org.begin_run(addr)
    org.start_run_log(addr)


def read(org, addr):
    org.begin_run(addr)
    org.end_run(addr, ok=True)


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


@pytest.fixture
def blocked(org, task):
    """The A4 situation: ceo reported the task blocked (it needs more runs) and root has read the news."""
    run(org, "ceo")
    org.report("ceo", task.id, "blocked", "Out of budget for the rework.")
    org.end_run("ceo", ok=True)
    read(org, ROOT)
    return task


def grant(org, n=3):
    return org.send(ROOT, "ceo", "Here are more runs.", budget=n)


# ------------------------------------------------------------------------------------------- waiting


def test_a_blocked_task_whose_lead_has_a_grant_waiting_is_waited_for(org, blocked):
    grant(org)
    assert work_in_flight(org)

    def finish():
        run(org, "ceo")
        org.report("ceo", blocked.id, "done", "All fixed.")
        org.end_run("ceo", ok=True)

    clock = Clock({3: finish})
    out = waiting(org, clock)
    assert not out.startswith("Nothing to wait for")
    assert out.splitlines()[0] == 'Changed after waiting 6s: "Write the report": blocked -> done'
    assert clock.sleeps == 3


def test_it_keeps_waiting_while_the_lead_works_and_times_out_with_the_lines(org, blocked):
    grant(org)
    run(org, "ceo")  # in flight
    clock = Clock()
    out = waiting(org, clock, wait=10, poll=5)
    assert out.startswith("Waited 10s: no task finished") and clock.now == 10


def test_an_agent_deeper_in_the_team_counts(org, blocked):
    org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=3)  # unread work for eng, ceo has the blocked task
    assert work_in_flight(org)
    assert not waiting(org, Clock(), wait=4).startswith("Nothing to wait for")


def test_nothing_can_run_returns_at_once(org, blocked):
    clock = Clock()
    out = waiting(org, clock)
    assert out.startswith("Nothing to wait for") and "blocked:" in out and clock.sleeps == 0
    assert not work_in_flight(org)


@pytest.mark.parametrize("why", ["no budget", "paused", "no mail"])
def test_unread_mail_that_cannot_run_does_not_count(org, blocked, why):
    if why == "no mail":
        read(org, "ceo")
    else:
        org.send(ROOT, "ceo", "hello")
    if why == "no budget":
        org.send("ceo", ROOT, "giving back", budget=org.budget("ceo"))
    if why == "paused":
        org.pause("ceo", "failures")
    assert not work_in_flight(org)
    assert waiting(org, Clock()).startswith("Nothing to wait for")


def test_a_budget_pause_with_budget_back_still_counts(org, blocked):
    org.pause("ceo", "budget")  # the scheduler lifts it at its next tick
    grant(org)
    assert work_in_flight(org)


def test_quiet_mail_does_not_wake_so_it_does_not_count(org, blocked):
    org.notify("ceo", "refund", "returned", wake=False)
    assert not work_in_flight(org)


def test_the_wait_ends_when_the_last_thing_that_could_run_stops(org, blocked):
    grant(org)

    def ceo_reads_and_stops():  # runs, finds nothing to do, sends nothing and the task stays blocked
        run(org, "ceo")
        org.end_run("ceo", ok=True)

    clock = Clock({1: ceo_reads_and_stops})
    out = waiting(org, clock, wait=60)
    assert out.splitlines()[0].startswith("Stopped after waiting 4s: nothing in the org can run any more")
    assert clock.sleeps == 2  # confirmed on a second look; it did not run out the clock


def test_a_short_gap_between_runs_is_not_the_end(org, blocked):
    grant(org)

    def hand_over():  # ceo ends its run having mailed eng: someone can always run
        run(org, "ceo")
        org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=2)
        org.end_run("ceo", ok=True)

    clock = Clock({1: hand_over})
    out = waiting(org, clock, wait=6, poll=2)
    assert out.startswith("Waited 6s:")


def test_a_finished_task_is_not_waited_for_even_with_leftover_mail(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    org.send(ROOT, "ceo", "thanks")
    assert not work_in_flight(org)
    assert waiting(org, Clock()).startswith("Nothing to wait for")


def test_describe_progress_does_not_wait_for_a_stopped_scheduler_even_for_a_blocked_task(org, blocked):
    grant(org)
    out = describe_progress(org, None, 600)
    assert out.startswith("Not waiting: no scheduler is running")
    assert "agents have work they could do" in out.splitlines()[-1] and "start()" in out.splitlines()[-1]


def test_describe_progress_waits_for_a_running_scheduler_on_a_blocked_task(org, blocked):
    grant(org)
    scheduler = FakeSchedulerStatus(SchedulerState("running", 1, "x"))
    view = SpyProgressView("lines")
    reporter = DerivedProgressReporter(view, FixedSnapshots(), scheduler, wire_attention.waiting_on_user_of(org.runtime), org.runtime.task_query)
    assert reporter.describe_progress(None, 30).endswith("scheduler: running (pid 1, since x)")
    assert view.kwargs == {"wait_seconds": 30}


# ------------------------------------------------------------------------------------------ Needs you


def test_every_unread_note_is_listed_with_its_id_including_the_first_budget_request(org, task):
    first = org.send("ceo", ROOT, "I need 2 more runs for the rework.\nDetails follow.", title="Budget request")
    second = org.send("ceo", ROOT, "BLOCKED: no budget left", title="BLOCKED: out of runs")
    org.notify(ROOT, "ceo is out of budget", "`ceo` has no budget left.")
    org.notify(ROOT, "refund", "returned", wake=False)  # quiet
    out = progress(org).splitlines()
    needs = [line for line in out if line.startswith("Needs you")]
    assert len(needs) == 3
    assert needs[0] == f'Needs you: note from ceo "Budget request": I need 2 more runs for the rework (message {first.id})'
    assert f"(message {second.id})" in needs[1] and needs[2].startswith("Needs you: runtime notice")


def test_a_done_result_is_not_listed_but_failed_and_blocked_are(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    assert not [line for line in progress(org).splitlines() if line.startswith("Needs you")]
    other = org.delegate(ROOT, ENG, "Other", "goal", "criteria", budget=2)
    run(org, ENG)
    org.report(ENG, other.id, "failed", "no luck")
    needs = [line for line in progress(org).splitlines() if line.startswith("Needs you")]
    assert len(needs) == 1 and needs[0].startswith("Needs you: failed result from ceo/eng")


def test_a_note_that_starts_with_a_blank_line_gets_its_first_real_line(org):
    m = org.send("ceo", ROOT, "\n\n  Please advise.", title="Q")
    assert f'Q": Please advise (message {m.id})' in progress(org)


# ---------------------------------------------------------------------------------------- run counts


def runs_line(org, task):
    return progress(org, task.id).splitlines()[0]


def test_runs_after_a_blocked_result_and_a_grant_are_counted(org, task):
    run(org, "ceo")
    run(org, "ceo")
    org.report("ceo", task.id, "blocked", "Need more runs.")
    org.end_run("ceo", ok=True)
    assert "runs 2 of 8." in runs_line(org, task)
    grant(org, 3)
    org.send(ROOT, ENG, "and for you", budget=2)  # a grant to anyone in the team counts too
    run(org, "ceo")
    org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=1)
    run(org, ENG)
    assert "runs 4 of 13." in runs_line(org, task)  # A4: it said "20 of 22" when 23 had been used


def test_a_single_task_org_matches_the_runs_in_status_and_health(org, task):
    for _ in range(3):
        run(org, "ceo")
    org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=2)
    run(org, ENG)
    grant(org, 2)
    used = sum(org.runs_used(a) for a in org.agents())
    assert f"runs {used} of 10." in runs_line(org, task)
    assert used == 4


def test_the_final_result_closes_the_window(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    org.end_run("ceo", ok=True)
    run(org, "ceo")  # a later run (for something else) is not this task's
    assert "runs 1 of 8 (7 returned)." in runs_line(org, task)
    org.send(ROOT, "ceo", "unrelated grant", budget=5)
    assert "runs 1 of 8 (7 returned)." in runs_line(org, task)


def test_overlapping_tasks_to_the_same_agent_do_not_count_a_run_twice(org, task):
    run(org, "ceo")
    second = org.delegate(ROOT, "ceo", "Second", "goal", "criteria", budget=3)
    run(org, "ceo")
    run(org, "ceo")
    assert "runs 1 of 8." in runs_line(org, task)
    assert "runs 2 of 3." in runs_line(org, second)
