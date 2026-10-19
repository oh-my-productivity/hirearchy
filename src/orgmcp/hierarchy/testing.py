"""The hierarchy rules over an organization on disk and over one kept in memory: what the contract suites iterate over.

``HierarchyWorld`` is what a test gets: ``Hiring`` and ``Retirement`` built over the real agents, access, settings, templates and delivery
of one organization (``fs_world``) or over their in-memory fakes (``memory_world``), the means to prepare the organization (agents, runs, messages,
ORG.md) and to look at what the rules did (files, events, mailboxes). Budgets are the numbers of a ``FixedBudget`` (moved by the messages delivered
through the world), so a test says "the team holds 7 runs" instead of building run logs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..access import AccessScopes, AuthorityPolicy, ModelResolver
from ..access.testing import StaticAccess, charters_on_disk
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..agents.testing import MemoryAgents, fs_agents
from ..budget.testing import FixedBudget, MovingDelivery
from ..delivery import MessageDelivery
from ..delivery.testing import DeliveryHarness, fs_pipeline, memory_pipeline
from ..kernel import Message, OrgPaths, join_frontmatter, norm
from ..kernel.testing import FakeClock, ListEventSink
from ..mail import MailboxReader, TaskQuery
from ..mail.testing import MemoryMailbox
from ..settings import OrgSettings
from ..settings.testing import fs_org_settings
from ..templates.testing import static_document_templates, static_notices
from ._hiring import RuleHiring
from ._ports import AgentSlots
from ._retirement import RuleRetirement
from ._slots import FsAgentSlots
from .api import Hiring, Retirement

ORG_MD = "---\nmission: test\n---\nrules\n"  # the ORG.md every world starts with: the defaults of the settings
CHARTER_BODY = "# Role\n\nDo the work.\n"


class MemoryAgentSlots(AgentSlots):
    """The places of the agents in a ``MemoryAgents``: occupied by a directory or a file."""

    def __init__(self, agents: MemoryAgents) -> None:
        self._agents = agents

    def occupied(self, addr: str) -> bool:
        a = norm(addr)
        return a in self._agents.dirs or a in self._agents.files


class _LoggedDelivery(MessageDelivery):
    """A delivery that keeps every message that went through it, in order (what the contract suites read to see what the rules wrote)."""

    def __init__(self, inner: MessageDelivery, log: list[Message]) -> None:
        self._inner = inner
        self._log = log

    def deliver(self, msg: Message) -> Message:
        done = self._inner.deliver(msg)
        self._log.append(done)
        return done

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        done = self._inner.notify(to, title, body, wake, trace)
        self._log.append(done)
        return done


@dataclass(frozen=True)
class HierarchyWorld:
    """``Hiring`` and ``Retirement`` over one organization, and the means to prepare and inspect it. Addresses: ``ceo``, ``ceo/eng``, ...; root exists."""

    hiring: Hiring
    retirement: Retirement
    agents: AgentDirectory  # the agents the rules read
    charters: CharterReader
    tasks: TaskQuery
    mail: MailboxReader
    budget: FixedBudget  # the numbers: ``held``, moved by ``post`` (a grant, a refund) and ``use_run``
    events: ListEventSink  # what the rules emitted
    clock: FakeClock
    root: Path  # the organization directory as the rules see it (an input must lie outside it)
    agent: Callable[[str, Mapping[str, object] | None], None]  # (addr, charter frontmatter): the agent exists; None means a plain worker
    post: Callable[[Message], Message]  # deliver a message (completed like a real one), and move the runs it carries
    use_run: Callable[[str], None]  # the agent makes one run (one run less)
    configure: Callable[[str], None]  # ORG.md becomes this text
    delivered: list[Message]  # every message delivered so far, by a test or by a rule, in order
    inbox: Callable[[str], list[Message]]
    sent: Callable[[str], list[Message]]
    read: Callable[[str], str | None]  # the text of a file of the organization (relative path), None when there is none
    listing: Callable[[str], list[str] | None]  # the sorted names in a directory of the organization, None when there is none
    put_dir: Callable[[str], None]  # an empty directory of the organization (a stray: no agent)


def _assemble(
    pipeline: DeliveryHarness,
    clock: FakeClock,
    *,
    agents: AgentDirectory,
    charters: CharterReader,
    registry: AgentRegistry,
    slots: AgentSlots,
    scopes: AccessScopes,
    authority: AuthorityPolicy,
    models: ModelResolver,
    settings: OrgSettings,
    root: Path,
    put: Callable[[str, str], None],
    read: Callable[[str], str | None],
    listing: Callable[[str], list[str] | None],
    put_dir: Callable[[str], None],
    configure: Callable[[str], None],
) -> HierarchyWorld:
    mail = pipeline.mail
    assert mail is not None
    budget = FixedBudget(mail.tasks, agents, charters)
    delivered: list[Message] = []
    delivery: MessageDelivery = _LoggedDelivery(MovingDelivery(pipeline.delivery, budget), delivered)
    events = ListEventSink()

    def agent(addr: str, meta: Mapping[str, object] | None = None) -> None:
        put(f"{addr}/AGENT.md", join_frontmatter(dict(meta) if meta is not None else {"role": "Worker"}, CHARTER_BODY))
        for sub in ("inbox", "inflight", "read", "sent", "runs", "work"):
            put_dir(f"{addr}/{sub}")

    def use_run(addr: str) -> None:
        budget.spend(addr)

    return HierarchyWorld(
        hiring=RuleHiring(
            agents, charters, registry, slots, settings, static_document_templates(), scopes, authority, models, clock, events,
        ),
        retirement=RuleRetirement(agents, registry, mail.tasks, budget, delivery, static_notices(), clock, events),
        agents=agents,
        charters=charters,
        tasks=mail.tasks,
        mail=mail.reader,
        budget=budget,
        events=events,
        clock=clock,
        root=root,
        agent=agent,
        post=delivery.deliver,
        use_run=use_run,
        configure=configure,
        delivered=delivered,
        inbox=pipeline.inbox,
        sent=pipeline.sent,
        read=read,
        listing=listing,
        put_dir=put_dir,
    )


def fs_world(tmp_path: Path) -> HierarchyWorld:
    """The real classes over the files of an organization directory."""
    pipeline = fs_pipeline(tmp_path)
    disk = fs_agents(tmp_path)
    access = charters_on_disk(tmp_path)
    document = fs_org_settings(tmp_path)
    document.put(ORG_MD)
    return _assemble(
        pipeline, pipeline.clock,
        agents=disk.directory, charters=disk.charters, registry=disk.registry, slots=FsAgentSlots(OrgPaths(tmp_path)),
        scopes=access.scopes, authority=access.authority, models=access.models, settings=document.settings, root=tmp_path,
        put=disk.put, read=disk.read, listing=disk.listing, put_dir=disk.put_dir, configure=document.put,
    )


def memory_world(tmp_path: Path) -> HierarchyWorld:
    """The in-memory fakes."""
    pipeline = memory_pipeline(tmp_path)
    box = pipeline.mail.reader if pipeline.mail is not None else None
    assert isinstance(box, MemoryMailbox)
    files = box.agents
    static = StaticAccess(agents=files, org_md=ORG_MD)
    return _assemble(
        pipeline, pipeline.clock,
        agents=files, charters=files, registry=files, slots=MemoryAgentSlots(files),
        scopes=static, authority=static, models=static, settings=static.settings, root=files.root,
        put=files.put, read=files.read, listing=files.listing, put_dir=files.put_dir, configure=static.put_config,
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    Hiring: [fs_world, memory_world],
    Retirement: [fs_world, memory_world],
}

__all__ = ["HierarchyWorld", "IMPLEMENTATIONS", "MemoryAgentSlots", "fs_world", "memory_world"]
