"""``ReserveAllocationPolicy``: which collaborator it asks, and when (the table of results is the contract suite's)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.budget import BudgetQuery
from orgmcp.budget._policy import ReserveAllocationPolicy
from orgmcp.budget.testing import BudgetWorld, fixed_world
from orgmcp.kernel import Message, OrgError
from orgmcp.settings.testing import MemoryOrgSettings

from ._support import assign, grant, populated, report


pytestmark = pytest.mark.xfail(strict=True, reason="red: B-budget")


class SpiedBudget(BudgetQuery):
    """A budget that answers a number and remembers whom it was asked about."""

    def __init__(self, answer: int | None = 5) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def budget(self, addr: str) -> int | None:
        self.asked.append(addr)
        return self.answer

    def delegable(self, addr: str) -> tuple[int, int, int]:
        raise AssertionError("the policy does not ask what can be delegated")

    def grant_hint(self, addr: str) -> str:
        raise AssertionError("the policy does not ask for hints")


@pytest.fixture
def w(tmp_path: Path) -> BudgetWorld:
    return populated(fixed_world(tmp_path))


def policy(w: BudgetWorld, budget: BudgetQuery, default_budget: int = 10) -> ReserveAllocationPolicy:
    return ReserveAllocationPolicy(budget, w.tasks, w.mail, MemoryOrgSettings(f"---\ndefault_budget: {default_budget}\n---\nrules\n"))


def test_the_budget_comes_from_the_query_it_is_given(w: BudgetWorld) -> None:
    spy = SpiedBudget(3)
    with pytest.raises(OrgError, match="you have 3 run"):
        policy(w, spy).check_allocation("ceo", 3, True)
    assert spy.asked == ["ceo"]


def test_root_and_nothing_to_hand_down_ask_nobody(w: BudgetWorld) -> None:
    spy = SpiedBudget()
    policy(w, spy).check_allocation("root", 99, True)
    policy(w, spy).check_allocation("ceo", 0, True)
    assert policy(w, spy).default_budget("root") == 10 and spy.asked == []


def test_the_default_budget_of_the_settings_it_is_given_caps_the_delegation(w: BudgetWorld) -> None:
    assert policy(w, SpiedBudget(50), default_budget=4).default_budget("ceo") == 4
    assert policy(w, SpiedBudget(50), default_budget=4).default_budget("root") == 4


def test_a_budget_that_is_none_counts_as_nothing(w: BudgetWorld) -> None:
    with pytest.raises(OrgError, match="you have 0 run"):
        policy(w, SpiedBudget(None)).default_budget("ceo")


def test_a_return_that_is_ruled_out_before_the_budget_is_looked_at_never_asks_for_it(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    task = assign(w, "root", "ceo")
    spy = SpiedBudget()
    assert policy(w, spy).budget_to_return("ceo", task, "blocked") == 0
    stranger = Message(sender="ceo/eng", to="ceo", type="task", body="b", id="x")  # the assigner is not the parent
    assert policy(w, spy).budget_to_return("ceo", stranger, "done") == 0
    assert spy.asked == []


def test_a_return_that_is_free_to_go_asks_for_the_budget_once_and_never_returns_a_debt(w: BudgetWorld) -> None:
    task = assign(w, "root", "ceo")
    w.begin_run("ceo")
    spy = SpiedBudget(-3)
    assert policy(w, spy).budget_to_return("ceo", task, "done") == 0 and spy.asked == ["ceo"]
    spy.answer = 6
    assert policy(w, spy).budget_to_return("ceo", task, "failed") == 6


def test_the_tasks_come_from_the_task_query_it_is_given(w: BudgetWorld) -> None:
    task = assign(w, "root", "ceo")
    w.begin_run("ceo")
    answered = assign(w, "ceo", "ceo/eng")
    spy = SpiedBudget()
    assert policy(w, spy).budget_to_return("ceo", task, "done") == 0  # a delegation is outstanding
    report(w, answered)
    w.begin_run("ceo")
    assert policy(w, spy).budget_to_return("ceo", task, "done") == 5
