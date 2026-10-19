"""Contract of ``WaitingOnUser``: when every open root task cannot move without the user, why, and what the user can do about it.

The decision table (nothing runs and nothing could start, yet root waits for a result; then budget, repeated failures, a stalled holder or a gone assignee
say what is needed), its texts and its options verbatim, over an organization on disk and over memory. The analysis only reads."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.attention import Waiting, WaitingOnUser
from orgmcp.attention.testing import IMPLEMENTATIONS, AttentionWorld
from orgmcp.kernel import ROOT

from ._support import RED, give, make_world, read_it, stalled_on_budget

pytestmark = RED

ACCEPT = "accept what exists so far (the task stays open: tell the user, and stop() the scheduler)"


@pytest.fixture(params=IMPLEMENTATIONS[WaitingOnUser], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> AttentionWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.waiting, WaitingOnUser)
    return made


def waiting(w: AttentionWorld) -> Waiting:
    found = w.waiting.analyze()
    assert found is not None
    return found


# ------------------------------------------------------------------------------ nothing waits for the user


def test_nothing_waits_when_root_has_no_open_task(w: AttentionWorld) -> None:
    assert w.waiting.analyze() is None
    w.hire("ceo")
    assert w.waiting.analyze() is None


def test_nothing_waits_when_a_task_has_been_answered(w: AttentionWorld) -> None:
    task = give(w)
    w.answer(task, "done", "ok")
    assert w.waiting.analyze() is None


def test_nothing_waits_while_the_holder_can_run(w: AttentionWorld) -> None:
    give(w)
    assert w.waiting.analyze() is None  # ceo has the task unread and runs to spend


def test_nothing_waits_while_something_runs_in_flight(w: AttentionWorld) -> None:
    give(w)
    w.begin_run("ceo")
    assert w.waiting.analyze() is None  # the inflight mailbox counts as running
    w.end_run("ceo")
    assert w.waiting.analyze() is not None  # and once the run has ended, ceo holds the task and nothing runs


def test_nothing_waits_while_the_scheduler_says_something_runs(w: AttentionWorld) -> None:
    give(w)
    read_it(w, "ceo")
    assert w.waiting.analyze(running={"ceo"}) is None
    assert w.waiting.analyze(running=["ceo"]) is None


def test_the_given_running_set_replaces_the_inflight_mailboxes(w: AttentionWorld) -> None:
    give(w)
    w.begin_run("ceo")  # in flight on disk...
    assert w.waiting.analyze(running=set()) is not None  # ...but the scheduler knows better


def test_nothing_waits_while_an_orphaned_run_may_still_be_alive(w: AttentionWorld) -> None:
    give(w)
    read_it(w, "ceo")
    assert w.waiting.analyze(blocked={"ceo"}) is None
    assert w.waiting.analyze(blocked=()) is not None


def test_nothing_waits_while_an_agent_outside_the_task_can_start(w: AttentionWorld) -> None:
    give(w, "ceo", "Ship it", 5)
    read_it(w, "ceo")
    give(w, "ops", "Other", 2)  # a second task, unread and funded
    assert w.waiting.analyze() is None


# ------------------------------------------------------------------------------ budget


def test_a_task_that_cannot_be_served_for_lack_of_budget_needs_a_grant(w: AttentionWorld) -> None:
    stalled_on_budget(w)
    found = waiting(w)
    assert found.text == 'waiting on you: "Rework the report" needs budget (ceo out of runs)'
    assert found.options == f'Your options: grant runs with send(to="ceo", body="<why>", budget=N), then call start(); or {ACCEPT}.'
    assert found.settled is True


def test_a_grant_makes_the_task_runnable_again(w: AttentionWorld) -> None:
    stalled_on_budget(w)
    assert w.waiting.analyze() is not None
    w.delegate(ROOT, "ceo", "more runs please", 2)  # runs travel with a message
    assert w.waiting.analyze() is None


def test_an_agent_paused_for_budget_whose_budget_is_back_is_startable(w: AttentionWorld) -> None:
    stalled_on_budget(w)
    w.pause("ceo", "budget")
    w.delegate(ROOT, "ceo", "more", 2)
    assert w.waiting.analyze() is None


def test_a_paused_worker_deep_in_the_subtree_counts_and_the_budget_goes_to_the_assignee(w: AttentionWorld) -> None:
    give(w, "ceo", "Ship it", 6)
    w.hire("ceo/eng")
    w.begin_run("ceo")
    w.delegate("ceo", "ceo/eng", "Build", 1)
    w.end_run("ceo")
    w.use_run("ceo/eng")  # eng used its only run and has the unread task
    w.pause("ceo/eng", "budget")
    found = waiting(w)
    assert found.text == 'waiting on you: "Ship it" needs budget (ceo/eng out of runs)'
    assert found.options == f'Your options: grant runs with send(to="ceo", body="<why>", budget=N), then call start(); or {ACCEPT}.'


def test_only_three_agents_are_named_and_the_rest_counted(w: AttentionWorld) -> None:
    give(w, "ceo", "Ship it", 0)
    for name in "abcd":
        w.hire(f"ceo/{name}")
        w.write(ROOT, f"ceo/{name}", f"hello {name}", "b", True)
    found = waiting(w)
    assert found.text == 'waiting on you: "Ship it" needs budget (ceo, ceo/a, ceo/b and 2 more out of runs)'


# ------------------------------------------------------------------------------ failures


def test_an_agent_paused_for_failures_needs_a_human_resume(w: AttentionWorld) -> None:
    give(w)
    w.pause("ceo", "failures")
    found = waiting(w)
    assert found.text == 'waiting on you: "Ship it" needs you to resume ceo (it keeps failing)'
    assert found.options == f"Your options: a human runs `orgmcp resume ceo` and you call start(); or {ACCEPT}."
    assert found.settled is True


def test_any_pause_but_budget_counts_as_failing(w: AttentionWorld) -> None:
    give(w)
    w.pause("ceo", "paused by the user: lunch")
    assert waiting(w).text == 'waiting on you: "Ship it" needs you to resume ceo (it keeps failing)'


def test_failing_is_told_before_short_of_budget(w: AttentionWorld) -> None:
    give(w, "ceo", "Ship it", 1)
    w.use_run("ceo")
    w.pause("ceo", "failures")
    assert waiting(w).text == 'waiting on you: "Ship it" needs you to resume ceo (it keeps failing)'


# ------------------------------------------------------------------------------ a holder that does nothing


def test_a_holder_that_read_the_task_and_does_nothing_needs_a_decision(w: AttentionWorld) -> None:
    give(w)
    read_it(w, "ceo")
    found = waiting(w)
    assert found.text == 'waiting on you: "Ship it" needs a decision (ceo holds it and nothing is running)'
    assert found.options == f'Your options: send(to="ceo", body=<instructions or a changed task>) and call start(); or {ACCEPT}.'


def test_the_ladder_may_still_wake_the_holder_until_the_last_step_is_taken(w: AttentionWorld) -> None:
    task = give(w)
    read_it(w, "ceo")
    assert waiting(w).settled is False  # nobody was reminded yet
    w.nudged(task, 0)
    assert waiting(w).settled is False  # ceo was reminded; root has not been told
    w.nudged(task, 1)
    assert waiting(w).settled is True  # root was told: nothing else will happen


def test_the_ladder_climbs_as_high_as_the_holder_is_deep(w: AttentionWorld) -> None:
    give(w, "ceo", "Ship it", 6)
    w.hire("ceo/eng")
    w.begin_run("ceo")
    task = w.delegate("ceo", "ceo/eng", "Build", 1)
    w.end_run("ceo")
    read_it(w, "ceo/eng")
    found = waiting(w)
    assert found.text == 'waiting on you: "Ship it" needs a decision (ceo/eng holds it and nothing is running)'
    assert found.options == f'Your options: send(to="ceo", body=<instructions or a changed task>) and call start(); or {ACCEPT}.'
    assert found.settled is False
    w.nudged(task, 1)
    assert waiting(w).settled is False  # ceo was told; root has not been
    w.nudged(task, 2)
    assert waiting(w).settled is True


def test_a_ledger_entry_of_another_task_does_not_settle_the_ladder(w: AttentionWorld) -> None:
    give(w)
    read_it(w, "ceo")
    other = give(w, "ceo", "Another", 1)
    w.nudged(other, 1)
    assert waiting(w).settled is False


# ------------------------------------------------------------------------------ a task that has nowhere to go


def test_a_task_whose_assignee_no_longer_exists_needs_a_decision(w: AttentionWorld) -> None:
    give(w, "ceo", "Ship it", 5)
    w.retire("ceo")
    found = waiting(w)
    assert found.text == 'waiting on you: "Ship it" needs a decision (ceo no longer exists)'
    assert found.options == f"Your options: {ACCEPT}."
    assert found.settled is True


# ------------------------------------------------------------------------------ the run cap


def test_the_run_cap_counts_as_waiting(w: AttentionWorld) -> None:
    give(w)
    found = w.waiting.analyze(can_start=False)
    assert found is not None
    assert found.text == (
        'waiting on you: "Ship it" needs a decision (ceo holds it and nothing is running); the run cap (max_runs) was reached'
    )
    assert found.options == (
        'Your options: send(to="ceo", body=<instructions or a changed task>) and call start(); or start() again with a higher max_runs; '
        f"or {ACCEPT}."
    )


def test_the_run_cap_alone_does_not_make_the_user_wait_without_a_task(w: AttentionWorld) -> None:
    assert w.waiting.analyze(can_start=False) is None


def test_the_run_cap_is_told_after_the_budget_and_the_failures(w: AttentionWorld) -> None:
    stalled_on_budget(w)
    found = w.waiting.analyze(can_start=False)
    assert found is not None
    assert found.text == 'waiting on you: "Rework the report" needs budget (ceo out of runs); the run cap (max_runs) was reached'
    assert found.options == (
        'Your options: grant runs with send(to="ceo", body="<why>", budget=N), then call start(); or start() again with a higher max_runs; '
        f"or {ACCEPT}."
    )


def test_a_run_in_flight_still_hides_the_wait_when_the_cap_is_spent(w: AttentionWorld) -> None:
    give(w)
    assert w.waiting.analyze(running={"ceo"}, can_start=False) is None


# ------------------------------------------------------------------------------ several tasks


def test_every_task_is_told_in_the_order_it_was_given_and_equal_options_once(w: AttentionWorld) -> None:
    stalled_on_budget(w)  # "Rework the report" -> ceo, out of runs
    give(w, "ops", "Open the shop", 5)
    w.pause("ops", "failures")
    found = waiting(w)
    assert found.text == (
        'waiting on you: "Rework the report" needs budget (ceo out of runs); "Open the shop" needs you to resume ops (it keeps failing)'
    )
    assert found.options == (
        'Your options: grant runs with send(to="ceo", body="<why>", budget=N), then call start(); '
        f"or a human runs `orgmcp resume ops` and you call start(); or {ACCEPT}."
    )


def test_two_tasks_with_the_same_need_give_one_option(w: AttentionWorld) -> None:
    give(w, "ceo", "One", 1)
    give(w, "ceo", "Two", 0)
    w.use_run("ceo")
    found = waiting(w)
    assert found.options.count("grant runs with") == 1 and '"One"' in found.text and '"Two"' in found.text


def test_a_question_only_reads_the_organization(w: AttentionWorld) -> None:
    stalled_on_budget(w)
    before = (w.inbox("ceo"), w.inbox(ROOT))
    assert waiting(w) == waiting(w)
    assert (w.inbox("ceo"), w.inbox(ROOT)) == before
