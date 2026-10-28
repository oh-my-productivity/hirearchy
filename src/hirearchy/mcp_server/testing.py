"""Fakes for ``mcp_server``: an organization that is a set of directories (``MemoryOrgOpener``), the binding kept in memory (``MemoryBinding``), the resolver, the
factory and the runner that answer what they are told, scripted versions of the ports the tool groups take (so a test of a group says what the port answers and
reads what it was asked), and the registry the contract suites iterate over.

A test of a tool group builds the group over these, registers it on a ``FastMCP`` and calls the tools through the protocol (``asyncio.run(server.call_tool(...))``).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, TypeVar

from mcp.server.fastmcp import FastMCP

from ..access import ToolNaming
from ..agents.testing import MemoryAgents
from ..budget import BudgetQuery, BudgetReclaimer
from ..dispatch import MessageSender, TaskAssigner, TaskReporter
from ..health import AgentHealth, HealthAnalyzer, HealthRenderer, OrgHealth
from ..hierarchy import Hiring, Retired, Retirement
from ..kernel import ROOT, Message, OrgError, norm
from ..kernel.testing import DictEnvironment
from ..locator.testing import MemoryOrgLocator
from ..orgfiles import OrgFileReader, OrgFileWriter
from ..reflection import ServiceReports, ServiceSteps
from ..services import ServiceHints
from ..mail.testing import memory_mailbox
from ..telemetry import ProcessLabel
from ..telemetry.testing import MemoryEventSinks, MemoryProcessLabel, StackTraceScope, json_argument_summarizer
from ..traces import TraceLookup
from ._binding import OpenerBindings, OrgBinding
from ._factory import GroupedServerFactory
from ._instructions import InstructionText
from ._ports import InstalledSkill, OrgOpener, OrgPorts, ServerFactories, ToolGroup
from ._recorder import BatchCallTrace, ToolCallRecorder
from ._resolver import EnvBindingResolver
from ._serve import StdioMcpRunner
from .api import BindingResolver, McpServerFactory, McpServerRunner, OrgBindingPort

T = TypeVar("T")

# ------------------------------------------------------------------------------ the organization, the binding, the resolver


class MemoryOrgPorts(OrgPorts):
    """An opened organization: its root and the objects it answers for each port (``put``)."""

    def __init__(self, root: Path, objects: Mapping[type, object] | None = None) -> None:
        self._root = root
        self._objects: dict[type, object] = dict(objects or {})

    @property
    def root(self) -> Path:
        return self._root

    def put(self, port: type[T], obj: T) -> None:
        self._objects[port] = obj

    def get(self, port: type[T]) -> T:
        return self._objects[port]  # type: ignore[return-value]


class MemoryOrgOpener(OrgOpener):
    """The organizations are the set ``organizations`` of directories (no file is looked at); ``initialize`` adds one (or fails like a full disk)."""

    def __init__(self, organizations: set[Path] | None = None, objects: Mapping[type, object] | None = None) -> None:
        self.organizations = organizations if organizations is not None else set()
        self.objects = dict(objects or {})
        self.initialized: list[tuple[Path, str, Mapping[str, object] | None]] = []
        self.fails: OSError | None = None
        self.opened = 0

    def open(self, root: Path) -> OrgPorts:
        if root not in self.organizations:
            raise OrgError(f"not an organization (no ORG.md): {root}")
        self.opened += 1
        return MemoryOrgPorts(root, self.objects)

    def initialize(self, root: Path, mission: str, config: Mapping[str, object] | None) -> None:
        if self.fails is not None:
            raise self.fails
        if root in self.organizations:
            raise OrgError(f"already an organization: {root}")
        self.initialized.append((root, mission, config))
        self.organizations.add(root)


class MemoryBinding(OrgBindingPort):
    """The binding in memory: bound to ``root`` (or to none), the organization is there once ``exists`` is true. ``create`` makes it (an empty mission
    and a second creation are refused)."""

    def __init__(self, root: Path | None, exists: bool = False, pinned: bool = False, objects: Mapping[type, object] | None = None) -> None:
        self._root = root
        self._pinned = pinned
        self.exists = exists
        self._objects = dict(objects or {})
        self.created: list[tuple[str, str | None, str | None]] = []

    @property
    def root(self) -> Path | None:
        return self._root

    @property
    def pinned(self) -> bool:
        return self._pinned

    def peek(self) -> OrgPorts | None:
        return MemoryOrgPorts(self._root, self._objects) if self.exists and self._root is not None else None

    def get(self) -> OrgPorts:
        ports = self.peek()
        if ports is None:
            raise OrgError(self.missing_message())
        return ports

    def location(self) -> Path | None:
        return self._root if self.exists else None

    def missing_message(self) -> str:
        return f"no organization at {self._root} yet: call create_org(mission=...) first"

    def create(self, mission: str, default_model: str | None = None, path: str | None = None) -> OrgPorts:
        if self.exists:
            raise OrgError(f"an organization already exists at {self._root}; nothing was created. It is ready to use: call whoami or status")
        if not (mission or "").strip():
            raise OrgError("mission is required: say in a few sentences what the organization is for")
        if self._root is None:
            self._root = Path(path or "/memory/org")
        self.created.append((mission, default_model, path))
        self.exists = True
        return self.get()


class FixedBindingResolver(BindingResolver):
    """Resolves to the binding and the identity it is given."""

    def __init__(self, binding: OrgBindingPort, identity: str) -> None:
        self.binding = binding
        self.identity = identity
        self.resolved = 0

    def resolve(self) -> tuple[OrgBindingPort, str]:
        self.resolved += 1
        return self.binding, self.identity


# ------------------------------------------------------------------------------ the groups, the recorder, the factory, the runner


class RecordingGroup(ToolGroup):
    """A group of one tool, ``ping_<tag>``, that notes for whom it was registered."""

    def __init__(self, tag: str, registered: list[tuple[str, str]] | None = None) -> None:
        self.tag = tag
        self.registered = registered if registered is not None else []

    def register(self, mcp: FastMCP, me: str) -> None:
        self.registered.append((self.tag, me))

        def ping() -> str:
            """Answers its tag."""
            return self.tag

        mcp.tool(name=f"ping_{self.tag}")(ping)


class FixedServerFactory(McpServerFactory):
    """Builds a server with a tool ``ping_<identity>`` for the agents it knows (and for root); any other agent is refused. ``built`` lists the identities."""

    def __init__(self, agents: Sequence[str] = ("ceo",)) -> None:
        self.agents = tuple(agents)
        self.built: list[str] = []

    def build(self, me: str) -> FastMCP:
        identity = norm(me)
        if identity != ROOT and identity not in self.agents:
            raise OrgError(f"no such agent: {identity}")
        self.built.append(identity)
        mcp = FastMCP("hirearchy", instructions=f"instructions of {identity}")
        RecordingGroup(identity.replace("/", "_")).register(mcp, identity)
        return mcp


class ServedServerFactory(McpServerFactory):
    """Builds a server for the identity it is asked for that does not read stdin when it is run, and keeps the identities (``built``) and how often a
    server was run (``runs``)."""

    def __init__(self) -> None:
        self.built: list[str] = []
        self.runs = 0

    def build(self, me: str) -> FastMCP:
        self.built.append(me)
        server = FastMCP("hirearchy")

        def run(*args: object, **kwargs: object) -> None:
            self.runs += 1

        server.run = run  # type: ignore[method-assign]
        return server


class ServedFactories(ServerFactories):
    def __init__(self, factory: McpServerFactory) -> None:
        self.factory = factory
        self.bound: list[OrgBindingPort] = []

    def factory_for(self, binding: OrgBindingPort) -> McpServerFactory:
        self.bound.append(binding)
        return self.factory


class RecordingRunner(McpServerRunner):
    """What ``run`` must do, in memory: name the process, resolve, build for the identity, serve."""

    def __init__(self, label: ProcessLabel, resolver: BindingResolver, factory: McpServerFactory) -> None:
        self._label = label
        self._resolver = resolver
        self._factory = factory
        self.served: list[str] = []

    def run(self) -> None:
        self._label.set("mcp")
        _, me = self._resolver.resolve()
        self._factory.build(me)
        self.served.append(me)


# ------------------------------------------------------------------------------ scripted ports of the tool groups


class CallRecording(Protocol):
    """What a scripted port needs of its log: to add a call, and to read back the calls of one name."""

    calls: list[tuple[str, tuple[object, ...], dict[str, object]]]

    def add(self, name: str, *args: object, **kwargs: object) -> None: ...

    def of(self, name: str) -> list[tuple[tuple[object, ...], dict[str, object]]]: ...


class CallLog(CallRecording):
    """The calls a scripted port was asked, as ``(name, args, kwargs)``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def add(self, name: str, *args: object, **kwargs: object) -> None:
        self.calls.append((name, args, kwargs))

    def of(self, name: str) -> list[tuple[tuple[object, ...], dict[str, object]]]:
        return [(a, k) for n, a, k in self.calls if n == name]


class ScriptedTasks(TaskAssigner, TaskReporter):
    """``delegate`` and ``report`` return the messages they would deliver (``returned``: the runs a final result carries back); ``fails`` is raised instead."""

    def __init__(self, log: CallLog | None = None, returned: int = 0, fails: Exception | None = None) -> None:
        self.log = log or CallLog()
        self.returned = returned
        self.fails = fails

    def delegate(
        self, actor: str, to: str, title: str, goal: str, acceptance: str, inputs: Sequence[str] | None = None, budget: int | None = None,
        revises: str | None = None, source: str | None = None,
    ) -> Message:
        self.log.add("delegate", actor, to, title, goal, acceptance, inputs, budget, revises, **({} if source is None else {"source": source}))
        if self.fails is not None:
            raise self.fails
        return Message(actor, to, "task", goal, title=title, budget=3 if budget is None else budget, id="task-1")

    def report(
        self, actor: str, task_id: str, status: str, summary: str, artifacts: Sequence[str] | None = None, lessons: str | None = None,
    ) -> Message:
        self.log.add("report", actor, task_id, status, summary, artifacts, lessons)
        if self.fails is not None:
            raise self.fails
        return Message(actor, "boss", "result", summary, status=status, budget=self.returned, id="result-1")


class ScriptedSender(MessageSender):
    def __init__(self, log: CallLog | None = None) -> None:
        self.log = log or CallLog()

    def send(
        self, actor: str, to: str, body: str, *, type: str = "note", title: str = "", reply_to: str | None = None, status: str | None = None,
        budget: int = 0, revises: str | None = None, supersedes: str | None = None, service: str | None = None, contract: int | None = None,
        playbook: int | None = None, feedback: str | None = None, source: str | None = None, criterion: str | None = None, wake: bool = True,
        skip_route_check: bool = False, inherited: str | None = None, acknowledges: str | None = None,
    ) -> Message:
        self.log.add("send", actor, to, body, type=type, title=title, reply_to=reply_to, status=status, budget=budget, wake=wake,
                     skip_route_check=skip_route_check)
        return Message(actor, norm(to), type, body, title=title, budget=budget, id="note-1")


class HeldBudgets(BudgetQuery):
    """The budget of an agent is the number in ``held`` (root has no limit); the hint of a grant is the text in ``hints``."""

    def __init__(self, held: Mapping[str, int] | None = None, hints: Mapping[str, str] | None = None) -> None:
        self.held = dict(held or {})
        self.hints = dict(hints or {})

    def budget(self, addr: str) -> int | None:
        return None if norm(addr) == ROOT else self.held.get(norm(addr), 0)

    def delegable(self, addr: str) -> tuple[int, int, int]:
        return self.budget(addr) or 0, 0, 0

    def grant_hint(self, addr: str) -> str:
        return self.hints.get(norm(addr), "")


class ScriptedReclaimer(BudgetReclaimer):
    def __init__(self, log: CallLog | None = None) -> None:
        self.log = log or CallLog()

    def reclaim(self, actor: str, report: str, budget: int | None = None) -> Message:
        self.log.add("reclaim", actor, report, budget)
        return Message(norm(report), actor, "note", "", budget=7 if budget is None else budget, id="reclaim-1")


class ScriptedHints(ServiceHints):
    """The hint of a report on a service request is ``hint``; the text of a feedback is ``feedback``."""

    def __init__(self, hint: str = "", log: CallLog | None = None) -> None:
        self.hint = hint
        self.log = log or CallLog()

    def report_hint(self, actor: str, task: Message, status: str) -> str:
        self.log.add("report_hint", actor, task.id, status)
        return self.hint

    def feedback_text(self, msg: Message) -> str:
        return ""


class ScriptedHiring(Hiring):
    def __init__(self, log: CallLog | None = None) -> None:
        self.log = log or CallLog()

    def hire(
        self, actor: str, name: str, role: str, charter: str, *, model: str | None = None, tools: Sequence[str] | None = None,
        can_hire: bool = False, max_children: int = 5, workspace: str | None = None, inputs: Sequence[str] | None = None,
        approved: bool = False, kind: str | None = None, approved_in: str | None = None,
    ) -> str:
        self.log.add("hire", actor, name, role, charter, model=model, tools=tools, can_hire=can_hire, max_children=max_children,
                     workspace=workspace, inputs=inputs, approved=approved)
        return name if actor == ROOT else f"{actor}/{name}"


class ScriptedRetirement(Retirement):
    def __init__(self, refunded: int = 0, to: str | None = None, log: CallLog | None = None) -> None:
        self.refunded, self.to = refunded, to
        self.log = log or CallLog()

    def retire(self, actor: str, name: str, reason: str) -> str:
        return self.retire_team(actor, name, reason).addr

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        self.log.add("retire_team", actor, name, reason)
        return Retired(name if "/" in name else f"{actor}/{name}", self.refunded, self.to)


class ScriptedFiles(OrgFileReader, OrgFileWriter):
    """``read`` answers ``text``; ``write_noted`` answers the path it is given under ``root`` and ``note``."""

    def __init__(self, root: Path, text: str = "", note: str = "", log: CallLog | None = None) -> None:
        self.root, self.text, self.note = root, text, note
        self.log = log or CallLog()

    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        return self.root / path

    def read(self, path: str, actor: str | None = None) -> str:
        self.log.add("read", path, actor)
        return self.text

    def resolve_write(self, actor: str, path: str) -> Path:
        return self.root / path

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        return self.write_noted(actor, path, content, append)[0]

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        self.log.add("write_noted", actor, path, content, append)
        return self.root / path, self.note


class StaticNaming(ToolNaming):
    """The names of the tools: ``read`` / ``write``, except for the agents in ``shadowed``, whose built-ins hide them (``org_read`` / ``org_write``)."""

    def __init__(self, shadowed: Mapping[str, tuple[str, str]] | None = None) -> None:
        self.shadowed = dict(shadowed or {})

    def tool_names(self, addr: str) -> dict[str, str]:
        read, write = self.shadowed.get(norm(addr), ("read", "write"))
        return {"read": read, "write": write}


class ScriptedReports(ServiceReports):
    def __init__(self, text: str = "", totals: Mapping[str, str] | None = None) -> None:
        self.text = text
        self.totals = dict(totals or {})

    def services_text(self, actor: str) -> str:
        return f"{self.text} [{actor}]"

    def case_total(self, task: Message) -> str:
        return self.totals.get(task.id, "")


class ScriptedSteps(ServiceSteps):
    """The next-step texts a test puts in; with ``raises`` set, every step raises it (the reading of the cases or the mail failed)."""

    def __init__(self, feedback: str = "", rework: str = "", raises: BaseException | None = None, watch: str = "") -> None:
        self.feedback = feedback
        self.rework = rework
        self.watch = watch
        self.raises = raises
        self.asked: list[tuple[str, ...]] = []

    def feedback_step(self, note: Message) -> str:
        self.asked.append(("feedback", note.id))
        if self.raises is not None:
            raise self.raises
        return self.feedback

    def rework_step(self, task: Message) -> str:
        self.asked.append(("rework", task.id))
        if self.raises is not None:
            raise self.raises
        return self.rework

    def watch_step(self, rejection: str) -> str:
        self.asked.append(("watch", rejection))
        if self.raises is not None:
            raise self.raises
        return self.watch


class FixedInstalledSkill(InstalledSkill):
    """The installed skill is out of date at ``path``, or is not (``None``)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path

    def stale(self) -> Path | None:
        return self.path


class ScriptedHealth(HealthAnalyzer, HealthRenderer):
    """The health of a subtree is an ``OrgHealth`` with no agents; the text of it is ``HEALTH of <root>``. The roots it was asked about are in ``asked``."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def agent_health(self, addr: str, now: datetime | None = None, limits: Mapping[str, float] | None = None) -> AgentHealth:
        raise OrgError("not scripted")

    def org_health(self, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
        self.asked.append(root)
        return OrgHealth(root, now or datetime(2026, 1, 1, tzinfo=timezone.utc), [], {})

    def render_text(self, health: OrgHealth, *, causes: bool = False) -> str:
        return f"HEALTH of {health.root}"


def agents_in(*addrs: str, can_hire: tuple[str, ...] = ()) -> MemoryAgents:
    """A directory with these agents (parents before children); the ones in ``can_hire`` may hire."""
    agents = MemoryAgents()
    for addr in addrs:
        agents.put(f"{addr}/AGENT.md", "---\nrole: R\n" + ("can_hire: true\n" if addr in can_hire else "") + "---\n# Role\n")
    return agents


# ------------------------------------------------------------------------------ the worlds of the contract suites


@dataclass
class BindingWorld:
    """A binding of a server to ``root``, and the means to make the organization there appear behind its back (``appear``)."""

    binding: OrgBindingPort
    root: Path
    appear: Callable[[], None]


def org_binding_over_memory_opener(tmp_path: Path) -> BindingWorld:
    root = tmp_path / "org"
    opener = MemoryOrgOpener()
    return BindingWorld(OrgBinding(root, opener), root, lambda: opener.organizations.add(root))


def memory_binding(tmp_path: Path) -> BindingWorld:
    root = tmp_path / "org"
    binding = MemoryBinding(root)

    def appear() -> None:
        binding.exists = True

    return BindingWorld(binding, root, appear)


@dataclass
class ResolverWorld:
    """A resolver, and the means to say who is asking: ``as_agent`` (an organization with this agent exists) or ``as_root`` (an organization exists at ``root``)."""

    resolver: BindingResolver
    root: Path
    as_agent: Callable[[str], None]
    as_root: Callable[[], None]


def env_binding_resolver(tmp_path: Path) -> ResolverWorld:
    root = tmp_path / "org"
    environment = DictEnvironment({"ORG_ROOT": str(root)}, cwd=tmp_path)
    opener = MemoryOrgOpener()
    locator = MemoryOrgLocator(environment, {root})

    def as_agent(addr: str) -> None:
        opener.organizations.add(root)
        environment.set("ORG_AGENT", addr)

    return ResolverWorld(EnvBindingResolver(environment, locator, opener, OpenerBindings(opener)), root, as_agent, lambda: opener.organizations.add(root))


def fixed_binding_resolver(tmp_path: Path) -> ResolverWorld:
    root = tmp_path / "org"
    binding = MemoryBinding(root)
    holder: dict[str, str] = {"identity": ROOT}
    resolver = _LateResolver(binding, holder)

    def as_agent(addr: str) -> None:
        binding.exists = True
        holder["identity"] = addr

    def as_root() -> None:
        binding.exists = True

    return ResolverWorld(resolver, root, as_agent, as_root)


class _LateResolver(BindingResolver):
    """``FixedBindingResolver`` whose identity is read when it resolves (the world says who is asking after the resolver is made)."""

    def __init__(self, binding: OrgBindingPort, holder: Mapping[str, str]) -> None:
        self._binding, self._holder = binding, holder

    def resolve(self) -> tuple[OrgBindingPort, str]:
        return self._binding, self._holder["identity"]


@dataclass
class FactoryWorld:
    """A factory of servers; ``known`` is an agent it serves, ``unknown`` one it does not, ``registered`` what its groups were registered for."""

    factory: McpServerFactory
    known: str
    unknown: str
    registered: list[tuple[str, str]] = field(default_factory=list)


def grouped_server_factory(tmp_path: Path) -> FactoryWorld:
    root = tmp_path / "org"
    registered: list[tuple[str, str]] = []
    binding = MemoryBinding(root, exists=True)
    agents = agents_in("ceo")
    text, mail = InstructionText(binding), memory_mailbox(tmp_path).reader
    trace = BatchCallTrace(text, lambda: NoTraces(), lambda: agents, lambda: mail)
    recorder = ToolCallRecorder(binding, MemoryEventSinks(), StackTraceScope(), json_argument_summarizer(tmp_path), trace)
    factory = GroupedServerFactory(binding, lambda: agents, text, recorder, [RecordingGroup("common", registered)], [RecordingGroup("root", registered)])
    return FactoryWorld(factory, "ceo", "nobody", registered)


def fixed_server_factory(tmp_path: Path) -> FactoryWorld:
    return FactoryWorld(FixedServerFactory(("ceo",)), "ceo", "nobody")


@dataclass
class RunnerWorld:
    runner: McpServerRunner
    label: ProcessLabel
    served: Callable[[], list[str]]  # the identities a server was built for


def stdio_runner(tmp_path: Path) -> RunnerWorld:
    label, factory = MemoryProcessLabel(), ServedServerFactory()
    binding = MemoryBinding(tmp_path / "org", exists=True)
    runner = StdioMcpRunner(label, FixedBindingResolver(binding, "ceo"), ServedFactories(factory))
    return RunnerWorld(runner, label, lambda: factory.built)


def recording_runner(tmp_path: Path) -> RunnerWorld:
    label, factory = MemoryProcessLabel(), FixedServerFactory(("ceo",))
    binding = MemoryBinding(tmp_path / "org", exists=True)
    runner = RecordingRunner(label, FixedBindingResolver(binding, "ceo"), factory)
    return RunnerWorld(runner, label, lambda: factory.built)


class NoTraces(TraceLookup):
    """No message has a trace."""

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        return None

    def open_task_traces(self, addr: str) -> list[str | None]:
        return []

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        return None, "ambiguous", []


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgBindingPort: [org_binding_over_memory_opener, memory_binding],
    BindingResolver: [env_binding_resolver, fixed_binding_resolver],
    McpServerFactory: [grouped_server_factory, fixed_server_factory],
    McpServerRunner: [stdio_runner, recording_runner],
}
