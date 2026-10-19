"""The budget ports over the mailboxes and run logs on disk, over the in-memory ones, and over numbers a test sets: what the contract suites iterate over.

``FixedBudget`` is the fake every consumer's test uses (``dispatch``, ``hierarchy``, ``eligibility``, ``health``, ...): the budget of an agent is a number
that the test sets, moved by the messages that are delivered through ``MovingDelivery``. ``BudgetWorld`` is what a test gets: the three ports, and the means
to prepare an organization (agents, messages, runs, ORG.md) and to look at its mailboxes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentDirectory, CharterReader
from ..agents.testing import fs_agents
from ..delivery import MessageDelivery
from ..delivery.testing import DeliveryHarness, fs_pipeline, memory_pipeline
from ..kernel import ROOT, RUNTIME, Message, norm
from ..kernel.testing import FakeClock
from ..mail import MailboxReader, TaskQuery
from ..mail.testing import MemoryMailbox
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ..settings.testing import fs_org_settings, memory_org_settings
from ._hint import grant_hint_text, most_delegable
from ._policy import ReserveAllocationPolicy
from ._query import DerivedBudgetQuery
from ._reclaim import NoteBudgetReclaimer
from .api import AllocationPolicy, BudgetQuery, BudgetReclaimer

ORG_MD = "---\nmission: test\n---\nrules\n"  # the ORG.md every world starts with: the defaults of the settings
LEAD = "---\nrole: Lead\ncan_hire: true\n---\n# Role: Lead\n\nLead the team.\n"  # the charter of an agent that can hire


class FixedBudget(BudgetQuery):
    """The budget of an agent is the number in ``held`` (an agent that is not there has 0; root has no limit). Messages that are delivered through
    a ``MovingDelivery`` move the runs they carry (``transfer``), a run that is used is ``spend``; the outstanding delegations and the charters
    are read from the mailboxes and the agents the fake is given, as the real query does."""

    def __init__(self, tasks: TaskQuery, agents: AgentDirectory, charters: CharterReader) -> None:
        self.held: dict[str, int] = {}
        self._tasks = tasks
        self._agents = agents
        self._charters = charters

    def transfer(self, sender: str, to: str, runs: int) -> None:
        """``runs`` leave ``sender`` and reach ``to`` (root and the runtime have no account)."""
        for addr, delta in ((norm(sender), -runs), (norm(to), runs)):
            if addr not in (ROOT, RUNTIME):
                self.held[addr] = self.held.get(addr, 0) + delta

    def spend(self, addr: str, runs: int = 1) -> None:
        """``addr`` makes ``runs`` more run(s)."""
        self.transfer(addr, RUNTIME, runs)

    def budget(self, addr: str) -> int | None:
        a = norm(addr)
        return None if a == ROOT else self.held.get(a, 0)

    def delegable(self, addr: str) -> tuple[int, int, int]:
        budget = self.budget(addr) or 0
        out = len(self._tasks.outstanding(addr))
        return budget, out, most_delegable(budget, out)

    def grant_hint(self, addr: str) -> str:
        if not self._agents.exists(addr) or not self._charters.charter(addr)[0].get("can_hire"):
            return ""
        budget, out, _ = self.delegable(addr)
        return grant_hint_text(addr, budget, out)


class MovingDelivery(MessageDelivery):
    """A delivery that tells a ``FixedBudget`` which runs a message moved (what the boxes and the run logs are to the derived budget)."""

    def __init__(self, inner: MessageDelivery, budget: FixedBudget) -> None:
        self._inner = inner
        self._budget = budget

    def deliver(self, msg: Message) -> Message:
        done = self._inner.deliver(msg)
        self._budget.transfer(done.sender, done.to, done.budget)
        return done

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        done = self._inner.notify(to, title, body, wake, trace)
        self._budget.transfer(done.sender, done.to, done.budget)
        return done


# ------------------------------------------------------------------------------ the world and the registry


@dataclass(frozen=True)
class BudgetWorld:
    """The three ports over one organization, and the means to prepare and inspect it. Addresses of agents: ``ceo``, ``ceo/eng``, ...; root exists."""

    query: BudgetQuery
    policy: AllocationPolicy
    reclaimer: BudgetReclaimer
    agents: AgentDirectory  # the agents the ports read
    tasks: TaskQuery  # the task views the ports read
    mail: MailboxReader  # the mailboxes the ports read
    clock: FakeClock
    fixed: FixedBudget | None  # the numbers a test may set directly; None when the budget is derived from the boxes and the run logs
    agent: Callable[[str, bool], None]  # (addr, can_hire): the agent exists, with a charter that says whether it can hire
    post: Callable[[Message], Message]  # deliver a message (completed like a real one), and move the runs it carries
    use_run: Callable[[str], None]  # the agent makes one run (consumes one run of budget)
    begin_run: Callable[[str], None]  # its inbox becomes the batch of a run in flight
    end_run: Callable[[str], None]  # the run ends well: the batch is read
    configure: Callable[[str], None]  # ORG.md becomes this text
    inbox: Callable[[str], list[Message]]
    sent: Callable[[str], list[Message]]


def _world(tmp_path: Path, pipeline: DeliveryHarness, runs: RunsHarness, fixed_budget: bool) -> BudgetWorld:
    mail = pipeline.mail
    assert mail is not None
    box = mail.reader
    agents: AgentDirectory
    charters: CharterReader
    if isinstance(box, MemoryMailbox):
        agents = charters = box.agents
        settings = memory_org_settings(tmp_path)
    else:
        disk = fs_agents(tmp_path)
        agents, charters = disk.directory, disk.charters
        settings = fs_org_settings(tmp_path)
    settings.put(ORG_MD)
    fixed = FixedBudget(mail.tasks, agents, charters) if fixed_budget else None
    delivery: MessageDelivery = MovingDelivery(pipeline.delivery, fixed) if fixed is not None else pipeline.delivery
    query: BudgetQuery = fixed if fixed is not None else DerivedBudgetQuery(mail.reader, runs.reader, agents, charters, mail.tasks)

    def agent(addr: str, can_hire: bool) -> None:
        mail.put(f"{addr}/AGENT.md", LEAD if can_hire else "---\nrole: Worker\n---\n# Role: Worker\n\nDo the work.\n")
        runs.add_agent(addr)

    def use_run(addr: str) -> None:
        runs.clock.advance(1)
        runs.writer.create(addr)
        if fixed is not None:
            fixed.spend(addr)

    def begin_run(addr: str) -> None:
        mail.batches.begin(addr)

    return BudgetWorld(
        query=query,
        policy=ReserveAllocationPolicy(query, mail.tasks, mail.reader, settings.settings),
        reclaimer=NoteBudgetReclaimer(delivery, query, mail.tasks, mail.reader, agents),
        agents=agents,
        tasks=mail.tasks,
        mail=mail.reader,
        clock=pipeline.clock,
        fixed=fixed,
        agent=agent,
        post=delivery.deliver,
        use_run=use_run,
        begin_run=begin_run,
        end_run=lambda addr: mail.batches.end(addr, True),
        configure=settings.put,
        inbox=pipeline.inbox,
        sent=pipeline.sent,
    )


def fs_world(tmp_path: Path) -> BudgetWorld:
    return _world(tmp_path, fs_pipeline(tmp_path), fs_runs(tmp_path), fixed_budget=False)


def memory_world(tmp_path: Path) -> BudgetWorld:
    return _world(tmp_path, memory_pipeline(tmp_path), memory_runs(tmp_path), fixed_budget=False)


def fixed_world(tmp_path: Path) -> BudgetWorld:
    return _world(tmp_path, memory_pipeline(tmp_path), memory_runs(tmp_path), fixed_budget=True)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    BudgetQuery: [fs_world, memory_world, fixed_world],
    AllocationPolicy: [fs_world, memory_world, fixed_world],
    BudgetReclaimer: [fs_world, memory_world, fixed_world],
}
