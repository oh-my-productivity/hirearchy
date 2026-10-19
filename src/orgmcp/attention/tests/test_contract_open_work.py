"""Contract of ``OpenWork``: is there nothing left to do, so that an until-done scheduler would exit at once?

True when root has no open task and no agent has work it could start (mail that wakes it, budget left, not paused for a reason a scheduler does not
lift itself). Runs in flight are not looked at: the question is asked of a scheduler that has none of its own. Over mailboxes on disk and in memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.attention import OpenWork
from orgmcp.attention.testing import IMPLEMENTATIONS, AttentionWorld
from orgmcp.kernel import ROOT

from ._support import RED, give, make_world, read_it, stalled_on_budget

pytestmark = RED


@pytest.fixture(params=IMPLEMENTATIONS[OpenWork], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> AttentionWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.work, OpenWork)
    return made


def test_an_organization_without_work_has_nothing_to_do(w: AttentionWorld) -> None:
    assert w.work.nothing_to_do() is True
    w.hire("ceo")
    assert w.work.nothing_to_do() is True


def test_an_open_root_task_is_something_to_do(w: AttentionWorld) -> None:
    give(w)
    assert w.work.nothing_to_do() is False


def test_an_open_root_task_that_nobody_can_serve_is_still_open(w: AttentionWorld) -> None:
    stalled_on_budget(w)
    assert w.work.nothing_to_do() is False


def test_an_answered_task_is_no_work(w: AttentionWorld) -> None:
    task = give(w)
    read_it(w, "ceo")
    w.answer(task, "done", "ok")
    assert w.work.nothing_to_do() is True


def test_a_blocked_answer_closes_the_task_for_root_until_it_is_taken_up_again(w: AttentionWorld) -> None:
    task = give(w)
    read_it(w, "ceo")
    w.answer(task, "blocked", "waiting for data")
    assert w.work.nothing_to_do() is True


def test_nothing_open_for_root_but_an_agent_with_mail_and_budget_is_something_to_do(w: AttentionWorld) -> None:
    task = give(w)
    w.answer(task, "done", "ok")  # answered before it was read: ceo still has the task in its inbox
    assert w.work.nothing_to_do() is False


def test_mail_that_does_not_wake_is_no_work(w: AttentionWorld) -> None:
    w.hire("ceo")
    w.fund("ceo", 3)
    read_it(w, "ceo")
    w.write(ROOT, "ceo", "fyi", "b", False)
    assert w.work.nothing_to_do() is True


def test_mail_without_budget_is_no_work(w: AttentionWorld) -> None:
    w.hire("ceo")
    w.write(ROOT, "ceo", "hello", "b", True)
    assert w.budget("ceo") == 0
    assert w.work.nothing_to_do() is True


def test_mail_for_an_agent_paused_for_failures_is_no_work(w: AttentionWorld) -> None:
    w.hire("ceo")
    w.fund("ceo", 3)
    read_it(w, "ceo")
    w.write(ROOT, "ceo", "hello", "b", True)
    w.pause("ceo", "failures")
    assert w.work.nothing_to_do() is True


def test_mail_for_an_agent_paused_for_budget_that_is_funded_again_is_work(w: AttentionWorld) -> None:
    w.hire("ceo")
    w.write(ROOT, "ceo", "hello", "b", True)
    w.pause("ceo", "budget")
    assert w.work.nothing_to_do() is True
    w.fund("ceo", 3)
    assert w.work.nothing_to_do() is False


def test_a_run_in_flight_is_not_looked_at(w: AttentionWorld) -> None:
    task = give(w)
    w.begin_run("ceo")
    w.answer(task, "done", "ok")
    assert w.work.nothing_to_do() is True
