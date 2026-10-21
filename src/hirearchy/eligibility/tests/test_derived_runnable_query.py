"""``DerivedRunnableQuery`` asks its collaborators, nothing more: the mail, the pause flag and the budget of the agents it walks."""

from __future__ import annotations

from collections.abc import Collection

from hirearchy.agents.testing import MemoryAgents
from hirearchy.budget import BudgetQuery
from hirearchy.eligibility._runnable import DerivedRunnableQuery
from hirearchy.eligibility.testing import MemoryPauseStore
from hirearchy.kernel import ROOT, Message
from hirearchy.kernel.testing import ListEventSink
from hirearchy.mail import MailboxReader
from hirearchy.mail.testing import MemoryMailbox


class RecordingBudget(BudgetQuery):
    """Every agent has 3 runs; the questions are kept."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def budget(self, addr: str) -> int | None:
        self.asked.append(addr)
        return None if addr == ROOT else 3

    def delegable(self, addr: str) -> tuple[int, int, int]:
        raise AssertionError("not eligibility's business")

    def grant_hint(self, addr: str) -> str:
        raise AssertionError("not eligibility's business")


class CountingMailbox(MailboxReader):
    """The unread count of the mailboxes behind, with the questions kept."""

    def __init__(self, inner: MemoryMailbox) -> None:
        self._inner = inner
        self.asked: list[str] = []

    def unread(self, addr: str) -> int:
        self.asked.append(addr)
        return self._inner.unread(addr)

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        return self._inner.messages(addr, *boxes)

    def received(self, addr: str) -> list[Message]:
        return self._inner.received(addr)

    def sent(self, addr: str) -> list[Message]:
        return self._inner.sent(addr)

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        return self._inner.find_received(addr, msg_id)

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        return self._inner.find_anywhere(addr, msg_id)

    def has_inflight(self, addr: str) -> bool:
        return self._inner.has_inflight(addr)


def build() -> tuple[DerivedRunnableQuery, RecordingBudget, CountingMailbox]:
    agents = MemoryAgents()
    for addr in ("ceo", "cto"):
        agents.put(f"{addr}/AGENT.md", "---\nrole: R\n---\nx\n")
    box = CountingMailbox(MemoryMailbox(agents))
    budget = RecordingBudget()
    return DerivedRunnableQuery(agents, box, MemoryPauseStore(ListEventSink()), budget), budget, box


def test_an_agent_without_mail_is_not_asked_about_its_budget() -> None:
    query, budget, box = build()
    assert query.runnable() == [] and budget.asked == [] and box.asked == ["ceo", "cto"]


def test_an_excluded_agent_is_not_asked_about_anything() -> None:
    query, budget, box = build()
    query.runnable(exclude=("ceo", "cto"))
    assert box.asked == [] and budget.asked == []


def test_an_agent_without_mail_is_not_startable_and_its_budget_is_not_asked() -> None:
    query, budget, _ = build()
    assert query.startable("ceo") is False and budget.asked == []
