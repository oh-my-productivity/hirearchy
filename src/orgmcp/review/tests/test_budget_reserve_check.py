"""``BudgetReserveCheck``: may a manager be written to? A note costs a run, and the runs a manager holds in reserve are not for notes."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.budget.testing import FixedBudget
from orgmcp.eligibility.testing import PauseHarness, memory_pauses
from orgmcp.kernel import Message
from orgmcp.mail.testing import MailHarness, MemoryMailbox, memory_mailbox
from orgmcp.review._ports import ReserveCheck
from orgmcp.review._reserve import BudgetReserveCheck


class Parts:
    def __init__(self, tmp_path: Path) -> None:
        self.mail: MailHarness = memory_mailbox(tmp_path)
        box = self.mail.reader
        assert isinstance(box, MemoryMailbox)
        self.pauses: PauseHarness = memory_pauses(tmp_path)
        self.budgets = FixedBudget(self.mail.tasks, box.agents, box.agents)
        self.check = BudgetReserveCheck(self.pauses.store, self.budgets, self.mail.tasks)

    def manager(self, budget: int, owed: int = 0) -> str:
        self.mail.agent("ceo")
        self.mail.agent("ceo/eng")
        self.budgets.held["ceo"] = budget
        for i in range(owed):
            self.mail.writer.store(Message(sender="ceo", to="ceo/eng", type="task", title=f"Job {i}", body="g", budget=1, id=f"2026010{i}T000000000000-ceo-0000"))
        return "ceo"


@pytest.fixture
def p(tmp_path: Path) -> Parts:
    made = Parts(tmp_path)
    assert isinstance(made.check, ReserveCheck)
    return made


def test_a_manager_with_budget_to_spare_may_be_written_to(p: Parts) -> None:
    assert p.check.why_not(p.manager(5)) == ""


def test_a_paused_manager_may_not(p: Parts) -> None:
    ceo = p.manager(5)
    p.pauses.store.pause(ceo, "failures")
    assert p.check.why_not(ceo) == "paused"


def test_paused_comes_before_no_budget(p: Parts) -> None:
    ceo = p.manager(0)
    p.pauses.store.pause(ceo, "failures")
    assert p.check.why_not(ceo) == "paused"


def test_a_manager_without_budget_may_not(p: Parts) -> None:
    assert p.check.why_not(p.manager(0)) == "no budget left"


def test_whoever_has_no_account_counts_as_without_budget(p: Parts) -> None:
    assert p.check.why_not("root") == "no budget left"  # the budget of root is unlimited (None), which is no budget to write a note with


def test_a_budget_no_more_than_the_outstanding_delegations_is_reserved(p: Parts) -> None:
    assert p.check.why_not(p.manager(1, owed=1)) == "budget 1 is reserved for 1 outstanding delegation(s)"


def test_a_budget_below_the_outstanding_delegations_is_reserved_too(p: Parts) -> None:
    assert p.check.why_not(p.manager(2, owed=3)) == "budget 2 is reserved for 3 outstanding delegation(s)"


def test_one_run_beyond_the_reserve_is_enough(p: Parts) -> None:
    assert p.check.why_not(p.manager(2, owed=1)) == ""
