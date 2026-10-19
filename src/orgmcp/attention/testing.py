"""The ``attention`` ports over an organization on disk and over memory, the fakes a consumer's test uses, and the registry the contract suites iterate over.

``AttentionWorld`` is an organization (agents, tasks, results, notes, run logs, pause flags, the ledger of the stall ladder) with the three ports over
it: built over the files of a temporary directory (``fs_world``) and over memory (``memory_world``), so that the ports are tested against both. Budgets
are the real ones, derived from the messages and the run logs (``orgmcp.budget.testing``), and what may start is the real ``RunnableQuery``.

``FixedWaiting``, ``ListHumanQueue`` and ``FixedOpenWork`` are what the tests of ``progress``, ``daemon``, ``scheduler`` and ``dashdata`` use instead of an
organization: each answers what it is told to, and keeps a record of what it was asked.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentRegistry
from ..agents.testing import fs_agents
from ..budget.testing import BudgetWorld
from ..budget.testing import fs_world as fs_budget_world
from ..budget.testing import memory_world as memory_budget_world
from ..eligibility.testing import PauseHarness, fs_pauses, memory_pauses, runnable_over
from ..kernel import ROOT, Message
from ..kernel.testing import FakeClock
from ..mail.testing import MemoryMailbox
from ..stalls.testing import MemoryNudges
from ._queue import InboxHumanQueue
from ._waiting import RootTaskWaitingOnUser
from ._work import RunnableOpenWork
from .api import HumanQueue, OpenWork, Waiting, WaitingOnUser


class FixedWaiting(WaitingOnUser):
    """``analyze`` answers ``waiting`` (``None``: nothing waits for the user) whatever it is asked, and keeps what it was asked in ``asked``."""

    def __init__(self, waiting: Waiting | None = None) -> None:
        self.waiting = waiting
        self.asked: list[tuple[Collection[str] | None, Collection[str], bool]] = []

    def analyze(self, *, running: Collection[str] | None = None, blocked: Collection[str] = (), can_start: bool = True) -> Waiting | None:
        self.asked.append((running, blocked, can_start))
        return self.waiting


class ListHumanQueue(HumanQueue):
    """The queue is the list ``entries`` of ``(message id, line)``."""

    def __init__(self, entries: Sequence[tuple[str, str]] = ()) -> None:
        self.entries = list(entries)

    def items(self) -> list[tuple[str, str]]:
        return list(self.entries)

    def lines(self) -> list[str]:
        return [line for _, line in self.entries]


class FixedOpenWork(OpenWork):
    """``nothing_to_do`` answers ``idle`` whatever it is asked, and keeps what it was asked in ``asked`` as ``(running, blocked, can_start)``."""

    def __init__(self, idle: bool = False) -> None:
        self.idle = idle
        self.asked: list[tuple[Collection[str], Collection[str], bool]] = []

    def nothing_to_do(self, *, running: Collection[str] = (), blocked: Collection[str] = (), can_start: bool = True) -> bool:
        self.asked.append((running, blocked, can_start))
        return self.idle


# ------------------------------------------------------------------------------ the world


@dataclass(frozen=True)
class AttentionWorld:
    """The three ports over one organization, and the means to set it up. Addresses of agents: ``ceo``, ``ceo/eng``, ...; root exists."""

    waiting: WaitingOnUser
    queue: HumanQueue
    work: OpenWork
    clock: FakeClock
    hire: Callable[[str], None]  # ``addr`` becomes an agent: no mail, no budget, no flag
    retire: Callable[[str], None]  # ``addr`` is retired (its directory is archived); what others sent it stays where it was sent from
    delegate: Callable[[str, str, str, int], Message]  # (sender, to, title, runs): a task, delivered with the runs it carries
    answer: Callable[[Message, str, str], Message]  # (task, status, body): the assignee reports; the result, delivered
    write: Callable[[str, str, str, str, bool], Message]  # (sender, to, title, body, wakes): a note, delivered
    fund: Callable[[str, int], Message]  # (addr, runs): a note of root that carries runs, delivered
    use_run: Callable[[str], None]  # the agent makes one run (it consumes one run of its budget)
    begin_run: Callable[[str], None]  # its inbox becomes the batch of a run in flight
    end_run: Callable[[str], None]  # the run ends well: the batch is read
    inbox: Callable[[str], list[Message]]  # the messages in the inbox of an address
    pause: Callable[[str, str], None]  # (addr, reason): the agent is paused
    budget: Callable[[str], int | None]  # the budget the ports see
    nudged: Callable[[Message, int], None]  # (task, step): the stall ladder has taken this step for the task
    configure: Callable[[str], None]  # ORG.md becomes this text


def _world(budgets: BudgetWorld, pauses: PauseHarness, registry: AgentRegistry) -> AttentionWorld:
    nudges = MemoryNudges(budgets.agents)
    runnable = runnable_over(budgets.agents, budgets.mail, pauses.store, budgets.query)

    def hire(addr: str) -> None:
        budgets.agent(addr, False)
        pauses.agent(addr)

    def retire(addr: str) -> None:
        registry.archive(addr, "20260101T000000")

    def delegate(sender: str, to: str, title: str, runs: int) -> Message:
        return budgets.post(Message(sender=sender, to=to, type="task", title=title, body="goal", budget=runs))

    def answer(task: Message, status: str, body: str) -> Message:
        return budgets.post(
            Message(sender=task.to, to=task.sender, type="result", title=f"re: {task.title}", body=body, reply_to=task.id, status=status),
        )

    def write(sender: str, to: str, title: str, body: str, wakes: bool) -> Message:
        return budgets.post(Message(sender=sender, to=to, type="note", title=title, body=body, wake=wakes))

    def fund(addr: str, runs: int) -> Message:
        return budgets.post(Message(sender=ROOT, to=addr, type="note", title="runs", body="more runs", budget=runs))

    def nudged(task: Message, step: int) -> None:
        nudges.save({**nudges.entries(), task.id: {"step": step, "at": budgets.clock.time()}})

    return AttentionWorld(
        RootTaskWaitingOnUser(budgets.tasks, budgets.agents, budgets.mail, pauses.store, budgets.query, runnable, nudges),
        InboxHumanQueue(budgets.mail),
        RunnableOpenWork(budgets.tasks, runnable),
        budgets.clock, hire, retire, delegate, answer, write, fund, budgets.use_run, budgets.begin_run, budgets.end_run, lambda addr: budgets.inbox(addr),
        pauses.store.pause, budgets.query.budget, nudged, budgets.configure,
    )


def fs_world(tmp_path: Path) -> AttentionWorld:
    """The ports over an organization directory."""
    return _world(fs_budget_world(tmp_path), fs_pauses(tmp_path), fs_agents(tmp_path).registry)


def memory_world(tmp_path: Path) -> AttentionWorld:
    """The ports over the in-memory mailboxes, run logs and flags."""
    budgets = memory_budget_world(tmp_path)
    box = budgets.mail
    assert isinstance(box, MemoryMailbox)
    return _world(budgets, memory_pauses(tmp_path), box.agents)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    WaitingOnUser: [fs_world, memory_world],
    HumanQueue: [fs_world, memory_world],
    OpenWork: [fs_world, memory_world],
}
