# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.daemon_world import waiting_on_user
from testkit.legacy.orgmcp.core import ROOT


# ------------------------------------------------------------------------------- until-done: waiting on the user
@pytest.fixture
def stalled_on_budget(org):
    """root's only task sits with ceo, which has used its single run: the task is unread and cannot be served."""
    task = org.delegate(ROOT, "ceo", "Rework the report", "Fix it", "It is fixed", budget=1)
    org.start_run_log("ceo")  # the one run is gone
    assert org.budget("ceo") == 0 and org.unread("ceo") == 1
    return task


def test_budget_stalled_task_is_waiting_on_the_user(org, stalled_on_budget):
    w = waiting_on_user(org)
    assert w.text == 'waiting on you: "Rework the report" needs budget (ceo out of runs)' and w.settled
    assert 'send(to="ceo", body="<why>", budget=N)' in w.options and "call start()" in w.options
    assert "accept what exists so far" in w.options and "stop()" in w.options


def test_paused_for_failures_asks_for_a_human_resume(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    org.pause("ceo", "failures")
    w = waiting_on_user(org)
    assert w.text == 'waiting on you: "Ship it" needs you to resume ceo (it keeps failing)'
    assert "`orgmcp resume ceo`" in w.options


def test_a_paused_worker_deep_in_the_subtree_counts_and_budget_goes_to_the_assignee(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=6)
    org.begin_run("ceo")
    org.delegate("ceo", "ceo/eng", "Build", "Build", "Built", budget=1)
    org.end_run("ceo", ok=True)
    org.start_run_log("ceo/eng")  # eng used its only run, has the unread task
    org.pause("ceo/eng", "budget")
    w = waiting_on_user(org)
    assert "needs budget (ceo/eng out of runs)" in w.text and 'send(to="ceo"' in w.options


def test_nothing_is_waiting_while_something_can_run_or_runs(org):
    assert waiting_on_user(org) is None  # no open task
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    assert waiting_on_user(org) is None  # ceo can run
    assert waiting_on_user(org, running={"ceo"}) is None  # or is running
    org.begin_run("ceo")
    assert waiting_on_user(org) is None  # inflight counts as running
    org.end_run("ceo", ok=True)
    assert waiting_on_user(org, blocked={"ceo"}) is None  # an orphaned run may still be alive


def test_a_grant_makes_the_task_runnable_again(org, stalled_on_budget):
    assert waiting_on_user(org)
    org.send(ROOT, "ceo", "more runs please", budget=2)
    assert waiting_on_user(org) is None


def test_the_run_cap_counts_as_waiting(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    w = waiting_on_user(org, can_start=False)
    assert "the run cap (max_runs) was reached" in w.text and "higher max_runs" in w.options
