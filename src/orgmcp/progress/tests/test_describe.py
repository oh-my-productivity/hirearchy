# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.daemon_world import describe_scheduler
from testkit.health_world import with_ports
from testkit.legacy.orgmcp.core import ROOT
from testkit.progress_world import describe_progress

from orgmcp.daemon import SchedulerState, SchedulerStatus
from orgmcp.daemon.testing import FakeSchedulerStatus


# ------------------------------------------------------------------------------- until-done: waiting on the user
@pytest.fixture
def stalled_on_budget(org):
    """root's only task sits with ceo, which has used its single run: the task is unread and cannot be served."""
    task = org.delegate(ROOT, "ceo", "Rework the report", "Fix it", "It is fixed", budget=1)
    org.start_run_log("ceo")  # the one run is gone
    assert org.budget("ceo") == 0 and org.unread("ceo") == 1
    return task


def test_progress_shows_the_reason_and_the_options_and_does_not_wait(org, stalled_on_budget):
    out = describe_progress(org, None, 300)
    assert out.startswith("Not waiting: nothing can progress without you. ")
    last = out.splitlines()[-1]
    assert last.startswith('scheduler: stopped (waiting on you: "Rework the report" needs budget (ceo out of runs)) - ')
    assert "nothing moves until you act" in last and 'send(to="ceo"' in last and "accept what exists so far" in last


def test_progress_while_the_scheduler_runs_still_says_so(org, stalled_on_budget, monkeypatch):
    with_ports(org, {SchedulerStatus: FakeSchedulerStatus(SchedulerState("running", 1, "x"))})
    out = describe_progress(org)
    assert 'waiting on you: "Rework the report" needs budget' in out and "exits by itself soon" in out


def test_status_line_of_an_org_that_can_progress_is_unchanged(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    assert describe_scheduler(org) == "scheduler: stopped"
    assert describe_progress(org).splitlines()[-1].startswith("scheduler: stopped - open tasks do not move")
