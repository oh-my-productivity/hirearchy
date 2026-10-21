"""``wire_attention``: the runtime has the three ports of ``attention``, built from the ports of the runtime."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from hirearchy.agents import AgentDirectory
from hirearchy.app import wiring
from hirearchy.attention import HumanQueue, OpenWork, Waiting, WaitingOnUser
from hirearchy.attention._queue import InboxHumanQueue
from hirearchy.attention._waiting import RootTaskWaitingOnUser
from hirearchy.attention._work import RunnableOpenWork
from hirearchy.budget import BudgetQuery
from hirearchy.budget.testing import FixedBudget
from hirearchy.eligibility import PauseStore, RunnableQuery
from hirearchy.eligibility.testing import MemoryPauseStore, runnable_over
from hirearchy.kernel import ROOT, RUNTIME, Message
from hirearchy.kernel.testing import ListEventSink
from hirearchy.mail import MailboxReader, TaskQuery
from hirearchy.mail._tasks import DerivedTaskQuery
from hirearchy.mail.testing import MemoryMailbox
from hirearchy.stalls import NudgeLedger
from hirearchy.stalls.testing import MemoryNudges

CHARTER = "---\nrole: R\n---\nx\n"


def test_the_runtime_has_the_three_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.waiting_on_user, RootTaskWaitingOnUser) and isinstance(runtime.waiting_on_user, WaitingOnUser)
    assert isinstance(runtime.human_queue, InboxHumanQueue) and isinstance(runtime.human_queue, HumanQueue)
    assert isinstance(runtime.open_work, RunnableOpenWork) and isinstance(runtime.open_work, OpenWork)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.waiting_on_user is not None and runtime.human_queue is not None and runtime.open_work is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    class Idle(OpenWork):
        def nothing_to_do(self, *, running: Collection[str] = (), blocked: Collection[str] = (), can_start: bool = True) -> bool:
            return True

    fake = Idle()
    runtime = wiring.open_runtime(tmp_path, {OpenWork: fake})
    assert runtime.open_work is fake and isinstance(runtime.human_queue, InboxHumanQueue)


def test_every_runtime_has_its_own_ports(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).human_queue is not wiring.open_runtime(tmp_path).human_queue


def test_every_collaborator_of_the_decision_comes_from_the_runtime(tmp_path: Path) -> None:
    """The whole decision over fakes: nothing of the organization directory is read or written."""
    box, events = MemoryMailbox(), ListEventSink()
    box.agents.put("ceo/AGENT.md", CHARTER)
    tasks, pauses = DerivedTaskQuery(box), MemoryPauseStore(events)
    budgets = FixedBudget(tasks, box.agents, box.agents)
    task = Message(sender=ROOT, to="ceo", type="task", title="T", body="g", id="20261018T100000000001-root-aaaa", budget=1)
    box.store(task)
    runtime = wiring.open_runtime(tmp_path, {
        AgentDirectory: box.agents, MailboxReader: box, TaskQuery: tasks, PauseStore: pauses, BudgetQuery: budgets,
        RunnableQuery: runnable_over(box.agents, box, pauses, budgets), NudgeLedger: MemoryNudges(box.agents),
    })
    assert runtime.waiting_on_user.analyze() is not None  # root waits for ceo, which has no runs
    assert runtime.waiting_on_user.analyze() == Waiting(
        'waiting on you: "T" needs budget (ceo out of runs)',
        'Your options: grant runs with send(to="ceo", body="<why>", budget=N), then call start(); or accept what exists so far '
        "(the task stays open: tell the user, and stop() the scheduler).",
    )
    assert runtime.open_work.nothing_to_do() is False
    box.store(Message(sender=RUNTIME, to=ROOT, type="note", title="Q", body="really?", id="20261018T100000000002-runtime-aaaa"))
    assert [line for _, line in runtime.human_queue.items()] == ['Needs you: runtime notice "Q": really? (message 20261018T100000000002-runtime-aaaa)']
    assert list(tmp_path.iterdir()) == []

