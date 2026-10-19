"""Which agents may start a run: waking mail, no pause, budget left."""

from __future__ import annotations

from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..eligibility import PauseStore
from ..mail import MailboxReader
from ..templates import Notices
from ._ports import Console, RunAdmission


class BudgetGate(RunAdmission):
    """An agent with no budget is paused and its parent told; a budget pause is lifted once budget is back."""

    def __init__(
        self, mail: MailboxReader, pauses: PauseStore, budgets: BudgetQuery, delivery: MessageDelivery, notices: Notices, console: Console
    ) -> None:
        raise NotImplementedError("red: D-sched-1")

    def admit(self, addr: str) -> bool:
        raise NotImplementedError("red: D-sched-1")
