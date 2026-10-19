"""``FixedBudget``: the numbers a test sets, moved by the messages delivered through ``MovingDelivery``."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.budget.testing import BudgetWorld, FixedBudget, fixed_world
from orgmcp.kernel import Message

from ._support import assign, grant, populated


RED = pytest.mark.xfail(strict=True, reason="red: B-budget")


@pytest.fixture
def w(tmp_path: Path) -> BudgetWorld:
    return populated(fixed_world(tmp_path))


def fixed(w: BudgetWorld) -> FixedBudget:
    assert w.fixed is not None
    return w.fixed


@RED
def test_an_agent_that_is_not_there_has_nothing(w: BudgetWorld) -> None:
    assert w.query.budget("ghost") == 0 and fixed(w).held == {}


@RED
def test_a_number_that_is_set_is_the_budget(w: BudgetWorld) -> None:
    fixed(w).held["ceo"] = 7
    assert w.query.budget("ceo") == 7 and w.query.delegable("ceo") == (7, 0, 6)


@RED
def test_root_has_no_limit_and_no_account(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 3)
    assert w.query.budget("root") is None and fixed(w).held == {"ceo": 3}


def test_a_delivered_message_moves_the_runs_it_carries(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    assign(w, "ceo", "ceo/eng", 2)
    assert fixed(w).held == {"ceo": 3, "ceo/eng": 2}


def test_a_notice_of_the_runtime_moves_nothing(w: BudgetWorld) -> None:
    fixed(w).held["ceo"] = 1
    w.post(Message(sender="runtime", to="ceo", type="note", body="b"))
    assert fixed(w).held == {"ceo": 1}


@RED
def test_a_run_that_is_spent_is_taken_from_the_agent(w: BudgetWorld) -> None:
    fixed(w).held["ceo"] = 3
    fixed(w).spend("ceo", 2)
    assert w.query.budget("ceo") == 1


@RED
def test_the_outstanding_delegations_are_read_from_the_mailboxes(w: BudgetWorld) -> None:
    fixed(w).held["ceo"] = 5
    assign(w, "ceo", "ceo/eng")
    assert w.query.delegable("ceo") == (5, 1, 3)
