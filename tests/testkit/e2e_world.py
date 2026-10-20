"""What the end-to-end tests (``tests/e2e``, ``tests/meta``) take from the application, over the composition root and the packages' ports.

The scenarios were written against the flat modules (``orgmcp.server.build_server``, ``orgmcp.observe.trace``, ``orgmcp.scheduler.Scheduler``,
``orgmcp.blueprint`` ...); those names are legacy (deleted by step E3), so a scenario takes them from here, where each is a thin call of a port of the
runtime (``org.runtime.trace_queries``, ``.message_parser`` ...), of the composition root (``orgmcp.app.wire_*``) or of the private class that owns the old
function (allowed here: ``testkit`` is not part of ``orgmcp``). The assertion text of the scenarios stays as it was; only their imports changed::

    from testkit.e2e_world import build_server, observe       # was: from orgmcp.server import build_server; from orgmcp import observe

``observe`` is a namespace with the old call shapes (``observe.trace(org, task_id)``); ``bpm`` and ``ex`` are the same for the few blueprint functions the
scenarios use; ``DashApp`` is the app of the organization at a root path.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from orgmcp.app import wire_dashboard, wire_mcp_server, wire_observability, wire_skill, wire_stalls, wiring
from orgmcp.app.wire_kiro import agents_dir
from orgmcp.blueprint import EXAMPLE_KINDS, Agent
from orgmcp.blueprint._access import PolicyAccessReport
from orgmcp.blueprint._accesswords import PlainAccessWords
from orgmcp.blueprint._org import NoOrgContext
from orgmcp.blueprint._pathcheck import RootedPathChecker
from orgmcp.blueprint._plan_texts import PLAN_DRAFT_HEADING, PLAN_HEADING
from orgmcp.blueprint._resolver import AgentResolver
from orgmcp.dashboard._app import DashApp as _DashApp
from orgmcp.dashboard._widgets import NavTable, TextPane
from orgmcp.kernel._system import OsEnvironment
from orgmcp.mcp_server._binding import OpenerBindings
from orgmcp.observability._messages import build_messages
from orgmcp.observability._render import TextObservabilityRenderer
from orgmcp.skill._source import PackagedSkillSource

__all__ = [
    "ROOT_INSTRUCTIONS", "DashApp", "NavTable", "TextPane", "agent_health", "binding_at", "bpm", "build_server", "ex", "file_confinement", "kiro_agents_dir",
    "load_message", "observe", "resolve_binding", "skill_source",
]

NO_ORG = Path("/nonexistent/orgmcp-no-org")  # a root nobody opens: the runtime of "no organization yet" (constructors do no I/O)
ROOT_INSTRUCTIONS = wire_mcp_server.ROOT_INSTRUCTIONS


# ------------------------------------------------------------------------------------------------------------ the MCP server
def binding_at(root: Path) -> Any:
    """The binding of a server to the organization at ``root`` (which need not exist yet)."""
    return OpenerBindings(wire_mcp_server.RuntimeOrgOpener()).bind(Path(root))


def build_server(org: Any, me: str) -> Any:
    """The MCP server for ``me``. ``org``: an ``Org`` (served over its runtime, as ``orgmcp mcp`` serves it once opened) or a binding (``binding_at``, ``resolve_binding``)."""
    if hasattr(org, "runtime"):
        binding = OpenerBindings(wire_mcp_server.RuntimeOrgOpener()).bind(org.root, wire_stalls.RuntimePorts(org.runtime))
    else:
        binding = org
    return wire_mcp_server.server_factory(binding).build(me)


def resolve_binding() -> tuple[Any, str]:
    """The binding of the environment (``ORG_ROOT``, ``ORG_AGENT`` ...) and who it acts as."""
    return wire_mcp_server.binding_resolver().resolve()


# ------------------------------------------------------------------------------------------------------------ observation
RuntimePorts = wire_stalls.RuntimePorts
_RENDERER = TextObservabilityRenderer()


class Observe:
    """The module-level functions of the former ``orgmcp.observe`` over the queries the composition root makes over ``org.runtime`` as it is when they are called
    (a test that replaces a port of the runtime - the scheduler's status - is seen); the text of a view is a pure function of the view."""

    @staticmethod
    def events(org: Any, since: Any = None, until: Any = None, agent: str | None = None, kind: str | None = None, trace: str | None = None,
               errors: bool = False, limit: int | None = None, now: datetime | None = None) -> Any:
        return wire_observability.event_queries(RuntimePorts(org.runtime)).events(since, until, agent, kind, trace, errors, limit, now)

    @staticmethod
    def trace(org: Any, task_id: str, now: datetime | None = None) -> Any:
        return wire_observability.trace_queries(RuntimePorts(org.runtime)).trace(task_id, now)

    @staticmethod
    def metrics(org: Any, since: Any = "24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> Any:
        return wire_observability.metric_queries(RuntimePorts(org.runtime)).metrics(since, by, now, agent)

    @staticmethod
    def now_view(org: Any, now: datetime | None = None) -> Any:
        return wire_observability.now_queries(RuntimePorts(org.runtime)).now_view(now)

    @staticmethod
    def check(org: Any, now: datetime | None = None) -> Any:
        return wire_observability.integrity_checks(RuntimePorts(org.runtime)).check(now)

    @staticmethod
    def render_trace(tr: Any, max_lines: int | None = None) -> str:
        return _RENDERER.render_trace(tr, max_lines)

    @staticmethod
    def render_metrics(m: Any, limit: int = 50) -> str:
        return _RENDERER.render_metrics(m, limit)

    @staticmethod
    def render_check(res: Any) -> str:
        return _RENDERER.render_check(res)

    @staticmethod
    def scan_messages(org: Any) -> Any:
        return org.runtime.message_index.scan()

    @staticmethod
    def build_messages(files: Any) -> Any:
        return build_messages(files)


observe = Observe()


def agent_health(org: Any, addr: str, now: datetime | None = None) -> Any:
    """``health.agent_health(org, addr, now)``: the measure of one agent, by the health analyzer of the runtime."""
    return org.runtime.health_analyzer.agent_health(addr, now)


def load_message(org: Any, path: Path) -> Any:
    """``Message.load(path)``: the message a file holds, parsed by the parser of the runtime of ``org``."""
    return org.runtime.message_parser.parse(path)


# ------------------------------------------------------------------------------------------------------------ the kiro files
def skill_source() -> Path:
    """The SKILL.md that ships with this install: inside the package (wheel) or in the source checkout."""
    return PackagedSkillSource(wire_skill.package_dir()).path()


def kiro_agents_dir() -> Path:
    """``~/.kiro/agents`` as the home of this process says it now."""
    return agents_dir(OsEnvironment())()


def file_confinement(org_root: Path, tools: list[str], workspace: Path | None, inputs: list[Path]) -> Any:
    """(allowedTools, toolsSettings) that confine kiro's built-in ``read``/``write`` by path (``KiroConfinementPolicy``)."""
    return wiring.open_runtime(NO_ORG).confinement_policy.file_confinement(org_root, tools, workspace, inputs)


# ------------------------------------------------------------------------------------------------------------ the dashboard
class DashApp(_DashApp):
    """The app of the organization at ``root`` (``now``: the time it shows)."""

    def __init__(self, root: str | Path, interval: float = 2.0, now: Any = None) -> None:
        super().__init__(wire_dashboard.queries_of(root, now), interval)


# ------------------------------------------------------------------------------------------------------------ the blueprint
class Examples:
    """The ready-to-edit blueprint templates by the old names."""

    KINDS = EXAMPLE_KINDS

    @staticmethod
    def example(kind: str = "research", base: Path | str = ".", service: bool = False) -> str:
        return wiring.open_runtime(NO_ORG).blueprint_examples.example(kind, base, service)


class Blueprint:
    """The old functions of ``orgmcp.blueprint`` that the scenarios use, over the runtime ports and the private classes that own them."""

    Agent = Agent
    PLAN_HEADING = PLAN_HEADING
    PLAN_DRAFT_HEADING = PLAN_DRAFT_HEADING

    @staticmethod
    def runtime(org: Any = None) -> Any:
        return org.runtime if org is not None else wiring.open_runtime(NO_ORG)

    def get_role(self, name: str) -> Any:
        return self.runtime().role_library.get_role(name)

    def validate(self, bp: Any, *, org: Any = None, allowed_roots: Sequence[str | Path] | None = None) -> Any:
        return self.runtime(org).blueprint_validator.validate(bp, org_exists=org is not None, allowed_roots=allowed_roots)

    def apply(self, org: Any, bp: Any, *, allowed_roots: Sequence[str | Path] | None = None) -> Any:
        return org.runtime.blueprint_applier.apply(bp, allowed_roots=allowed_roots)

    def _resolve(self, bp: Any, org: Any, roots: Any, issues: list[Any]) -> Any:
        rt = self.runtime(org)
        return AgentResolver(rt.role_library, RootedPathChecker(rt.environment)).resolve(bp, NoOrgContext(), roots, issues)

    def _access(self, agent: Any) -> str:
        return PolicyAccessReport(self.runtime().confinement_policy).line(agent)

    def _agent_access(self, agent: Any) -> str:
        return PlainAccessWords(PolicyAccessReport(self.runtime().confinement_policy)).describe(agent)


bpm = Blueprint()
ex = Examples()
