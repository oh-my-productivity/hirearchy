"""The protocol rules over the mailboxes on disk, over the in-memory ones and over budgets that are numbers, the fakes of the consumers, and the
registry the contract suites iterate over.

``DispatchWorld`` is what a test gets: the three ports (``sender``, ``assigner``, ``reporter``) and the private collaborators among them, over one
organization, and the means to prepare it (agents, messages, runs, ORG.md) and to look into its mailboxes. ``RecordingSender`` is the fake every
consumer's test uses (``services``, ``blueprint``, ``mcp_server``, ``cli``): it keeps the messages in a list instead of checking and delivering
them. ``NoReworkContext`` and ``FixedReworkContext`` are the stand-ins for the port that ``services`` implements.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..access import AccessScopes
from ..access.testing import AccessHarness, charters_on_disk, static_access
from ..agents import AgentDirectory
from ..budget import AllocationPolicy, BudgetQuery
from ..budget.testing import BudgetWorld
from ..budget.testing import fixed_world as budget_fixed_world
from ..budget.testing import fs_world as budget_fs_world
from ..budget.testing import memory_world as budget_memory_world
from ..delivery import MessageDelivery
from ..delivery.testing import RecordingDelivery
from ..kernel import RUNTIME, JsonObject, Message, OrgPaths, norm
from ..kernel.testing import FakeClock, SequenceIdGenerator
from ..mail import MailboxReader, TaskQuery
from ..settings import OrgSettings
from ..settings.testing import SettingsHarness, fs_org_settings, memory_org_settings
from ..templates.testing import static_document_templates
from ._artifacts import ArtifactAnnotator
from ._assigner import RuleTaskAssigner
from ._hops import InflightHopCounter
from ._lessons import LessonsPolicy
from ._protocols import HopCounter, RoutePolicy
from ._reporter import RuleTaskReporter
from ._routes import ParentSiblingRoutePolicy
from ._sender import RuleMessageSender, provenance_source
from .api import MessageSender, ReworkContext, TaskAssigner, TaskReporter

MEMORY_ROOT = Path("/memory/org")  # where the in-memory worlds pretend the organization is (no artifact exists there)
ORG_MD = "---\nmission: test\n---\nrules\n"  # the ORG.md every world starts with: the defaults of the settings


# ------------------------------------------------------------------------------ the fakes of the consumers


class RecordingSender(MessageSender):
    """Keeps every message it is asked to send, in order, as the delivered message: the addresses normalized, the body and the title stripped,
    ``hops`` 0. It checks nothing but provenance (S1-S3 and the ``relayed`` default for a root rework, verdict note or link note), which every
    ``MessageSender`` applies (no cap, no route, no budget): a consumer's test sets up what it needs and looks at ``messages``.
    ``route_check_skipped`` holds the ids of the messages that were sent with ``skip_route_check``."""

    def __init__(self, delivery: MessageDelivery) -> None:
        self._delivery = delivery
        self.messages: list[Message] = []
        self.route_check_skipped: list[str] = []

    def send(
        self, actor: str, to: str, body: str, *, type: str = "note", title: str = "", reply_to: str | None = None,
        status: str | None = None, budget: int = 0, revises: str | None = None, supersedes: str | None = None,
        service: str | None = None, contract: int | None = None, playbook: int | None = None, feedback: str | None = None,
        source: str | None = None, criterion: str | None = None, wake: bool = True, skip_route_check: bool = False,
        inherited: str | None = None,
    ) -> Message:
        source = provenance_source(norm(actor), type, revises, feedback, reply_to, source, criterion, inherited)
        msg = Message(
            sender=norm(actor), to=norm(to), type=type, body=body.strip(), title=title.strip(), reply_to=reply_to, status=status,
            budget=int(budget or 0), revises=revises, supersedes=supersedes, service=service, contract=contract, playbook=playbook,
            feedback=feedback, source=source, criterion=criterion, wake=wake,
        )
        done = self._delivery.deliver(msg)
        self.messages.append(done)
        if skip_route_check:
            self.route_check_skipped.append(done.id)
        return done


class NoReworkContext(ReworkContext):
    """Every task is an ordinary task: a rework inherits nothing."""

    def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
        return {}

    def work_tier(self, actor: str) -> str | None:
        return None


class FixedReworkContext(ReworkContext):
    """The service fields of the tasks a test names: ``{task id: {"service": ..., "contract": ..., "playbook": ...}}``; any other task is ordinary.
    ``tiers`` is the tier of the work each actor it names does (``{actor: "human"}``); any other actor works at none."""

    def __init__(self, fields: Mapping[str, Mapping[str, object]], tiers: Mapping[str, str] | None = None) -> None:
        self._fields = {task_id: dict(given) for task_id, given in fields.items()}
        self._tiers = dict(tiers or {})

    def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
        return dict(self._fields.get(revises, {}))

    def work_tier(self, actor: str) -> str | None:
        return self._tiers.get(actor)


class PostedDelivery(MessageDelivery):
    """A delivery that is a function (the ``post`` of a world, which may move runs): ``notify`` is a note of the runtime, delivered the same way."""

    def __init__(self, post: Callable[[Message], Message]) -> None:
        self._post = post

    def deliver(self, msg: Message) -> Message:
        return self._post(msg)

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        return self._post(Message(sender=RUNTIME, to=norm(to), type="note", title=title, body=body, wake=wake, trace=trace or None))


# ------------------------------------------------------------------------------ the world


@dataclass(frozen=True)
class DispatchWorld:
    """The ports over one organization, and the means to prepare and inspect it. Addresses of agents: ``ceo``, ``ceo/eng``, ...; root exists."""

    sender: MessageSender
    assigner: TaskAssigner
    reporter: TaskReporter
    routes: RoutePolicy
    hops: HopCounter
    agents: AgentDirectory  # the agents the ports read
    mail: MailboxReader  # the mailboxes the ports read
    tasks: TaskQuery
    query: BudgetQuery
    policy: AllocationPolicy
    scopes: AccessScopes
    settings: OrgSettings
    root: Path  # the organization directory as the ports see it (the artifacts are files below it, or in a workspace)
    clock: FakeClock
    agent: Callable[[str, bool], None]  # (addr, can_hire): the agent exists, with a charter that says whether it can hire
    put_agent: Callable[[str, Mapping[str, object]], None]  # the agent exists, with a charter with exactly this frontmatter
    post: Callable[[Message], Message]  # deliver a message straight (completed like a real one), whatever the rules say
    use_run: Callable[[str], None]  # the agent makes one run (consumes one run of budget)
    begin_run: Callable[[str], None]  # its inbox becomes the batch of a run in flight
    end_run: Callable[[str], None]  # the run ends well: the batch is read
    configure: Callable[[str], None]  # ORG.md becomes this text
    inbox: Callable[[str], list[Message]]
    sent: Callable[[str], list[Message]]
    assigner_with: Callable[[ReworkContext], TaskAssigner]  # the assigner of this world with another source of rework fields


def _world(budget: BudgetWorld, access: AccessHarness, settings: SettingsHarness, root: Path) -> DispatchWorld:
    delivery = PostedDelivery(budget.post)
    templates = static_document_templates()
    routes, hops = ParentSiblingRoutePolicy(budget.mail), InflightHopCounter(budget.mail)
    sender = RuleMessageSender(budget.agents, settings.settings, routes, budget.policy, hops, delivery)

    def assigner_with(rework: ReworkContext) -> TaskAssigner:
        return RuleTaskAssigner(budget.agents, budget.mail, templates, budget.policy, rework, sender)

    def put_agent(addr: str, meta: Mapping[str, object]) -> None:
        budget.agent(addr, bool(meta.get("can_hire")))  # the agent exists for the run logs and the directory ...
        access.put_agent(addr, JsonObject(meta))  # ... and its charter is exactly this

    def configure(text: str) -> None:
        budget.configure(text)
        settings.put(text)

    return DispatchWorld(
        sender=sender,
        assigner=assigner_with(NoReworkContext()),
        reporter=RuleTaskReporter(
            budget.agents, budget.mail, budget.tasks, templates, budget.policy, LessonsPolicy(),
            ArtifactAnnotator(OrgPaths(root), access.scopes), sender,
        ),
        routes=routes,
        hops=hops,
        agents=budget.agents,
        mail=budget.mail,
        tasks=budget.tasks,
        query=budget.query,
        policy=budget.policy,
        scopes=access.scopes,
        settings=settings.settings,
        root=root,
        clock=budget.clock,
        agent=lambda addr, can_hire: put_agent(addr, {"role": "Lead", "can_hire": True} if can_hire else {"role": "Worker"}),
        put_agent=put_agent,
        post=budget.post,
        use_run=budget.use_run,
        begin_run=budget.begin_run,
        end_run=budget.end_run,
        configure=configure,
        inbox=budget.inbox,
        sent=budget.sent,
        assigner_with=assigner_with,
    )


def fs_world(tmp_path: Path) -> DispatchWorld:
    access = charters_on_disk(tmp_path)  # first: it writes the default ORG.md, which the world replaces
    world = _world(budget_fs_world(tmp_path), access, fs_org_settings(tmp_path), tmp_path)
    world.configure(ORG_MD)
    return world


def memory_world(tmp_path: Path) -> DispatchWorld:
    world = _world(budget_memory_world(tmp_path), static_access(tmp_path), memory_org_settings(tmp_path), MEMORY_ROOT)
    world.configure(ORG_MD)
    return world


def fixed_world(tmp_path: Path) -> DispatchWorld:
    """In memory, and the budget of every agent is a number that the messages move (``budget.testing.FixedBudget``)."""
    world = _world(budget_fixed_world(tmp_path), static_access(tmp_path), memory_org_settings(tmp_path), MEMORY_ROOT)
    world.configure(ORG_MD)
    return world


def recording_world(tmp_path: Path) -> DispatchWorld:
    """The in-memory world whose sender is a ``RecordingSender``: only ``sender`` (and what is read back with ``inbox`` and ``sent``) is the fake."""
    base = memory_world(tmp_path)
    fake = RecordingSender(RecordingDelivery(base.clock, SequenceIdGenerator(base.clock)))
    return dataclasses.replace(
        base,
        sender=fake,
        inbox=lambda addr: [m for m in fake.messages if m.to == addr],
        sent=lambda addr: [m for m in fake.messages if m.sender == addr],
    )


def no_rework(tmp_path: Path) -> ReworkContext:
    return NoReworkContext()


def fixed_rework(tmp_path: Path) -> ReworkContext:
    return FixedReworkContext({"20260101T000000000001-ceo-aaaa": {"service": "weekly-brief", "contract": 3, "playbook": 2}})


PURE = {"GuardedSender"}  # one implementation over any sender (``GuardedRootSender``), no fake of its own: ``test_contract_guarded_sender`` runs it over three

IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    MessageSender: [fs_world, memory_world, fixed_world, recording_world],
    TaskAssigner: [fs_world, memory_world, fixed_world],
    TaskReporter: [fs_world, memory_world, fixed_world],
    ReworkContext: [no_rework, fixed_rework],
}
