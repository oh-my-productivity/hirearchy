"""Which agents may start a run: waking mail, no pause, budget left."""

from __future__ import annotations

from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..eligibility import PauseStore
from ..kernel import ROOT, parent, single
from ..mail import MailboxReader
from ..templates import Notices
from ._ports import Console, RunAdmission


class BudgetGate(RunAdmission):
    """An agent with no budget is paused and its parent told; a budget pause is lifted once budget is back."""

    def __init__(
        self, mail: MailboxReader, pauses: PauseStore, budgets: BudgetQuery, delivery: MessageDelivery, notices: Notices, console: Console
    ) -> None:
        self._mail, self._pauses, self._budgets, self._delivery, self._notices, self._console = mail, pauses, budgets, delivery, notices, console

    def admit(self, addr: str) -> bool:
        if not self._mail.unread(addr):
            return False
        reason = self._pauses.paused(addr)
        budget = self._budgets.budget(addr) or 0
        if reason == "budget" and budget > 0:
            self._pauses.resume(addr, "budget is back", by="runtime")
            reason = None
        if reason:
            return False
        if budget <= 0:
            self._pauses.pause(addr, "budget", by="runtime")
            waiting = [m.trace for m in self._mail.messages(addr, "inbox")]
            self._delivery.notify(parent(addr) or ROOT, f"{addr} is out of budget", self._notices.budget(addr, self._mail.unread(addr)),
                                  trace=single(waiting))
            self._console.say(f"{addr}: out of budget, paused, parent notified")
            return False
        return True
