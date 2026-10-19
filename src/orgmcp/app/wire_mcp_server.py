"""The MCP server over the ports of the organization its binding opens (ARCHITECTURE.md 6.3): the factory of servers, the resolver of the binding, the runner.

The server is not a port of the runtime (``NOT_A_FIELD`` of ``fields_mcp_server``): a server is made per binding and per identity. The binding holds an
*opener* (``RuntimeOrgOpener``), not a runtime, because the organization may not exist yet (setup mode); every tool group receives ``Provider`` thunks
of the narrow ports of the features, which ask the binding at tool-call time, so a server opens the runtime of its organization on its first tool call.
Process-scope objects (the sinks of the events, the trace scope, the process label) need no organization and are the process's own.

Heavy modules (the MCP framework, the tool groups) are imported when a server is made, not when the application package is loaded: every command of the
command line opens a runtime, and none of them but ``orgmcp mcp`` needs a server.

``LegacyOrgBinding``, ``legacy_build_server`` and ``legacy_resolve_binding`` serve the module ``orgmcp.server`` (a shim until E3): the constructor and the
functions the tests and the old callers use, and the patch point ``orgmcp.server.start_scheduler``. They go with it.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast

from ..daemon import SchedulerControl
from ..kernel import Environment, OrgError, Provider
from ..kernel._system import OsEnvironment
from ..mcp_server import BindingResolver, McpServerFactory, McpServerRunner, OrgBindingPort
from ..mcp_server._binding import OpenerBindings, OrgBinding
from ..mcp_server._instructions import DS_STORE, INSTRUCTIONS, ROOT_INSTRUCTIONS
from ..mcp_server._ports import BindingFactory, OrgOpener, OrgPorts, ServerFactories
from ._builder import Builder
from .wire_locator import os_locator
from .wire_stalls import RuntimePorts
from .wiring import open_runtime, process_resources, providers

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..blueprint._assembly import PlanParts
    from .facade import Org

T = TypeVar("T")

__all__ = [
    "DS_STORE", "INSTRUCTIONS", "ROOT_INSTRUCTIONS", "LegacyOrgBinding", "RuntimeOrgOpener", "WiredServerFactories", "binding_resolver",
    "legacy_build_server", "legacy_resolve_binding", "mcp_server_runner", "register", "serve", "server_factory",
]


def register(b: Builder) -> None:
    """The server has no port of its own (see the module docstring)."""


class RuntimeOrgOpener(OrgOpener):
    """The organizations of this process are opened with ``open_runtime``; a new one is initialized through the initializer of its own runtime."""

    def open(self, root: Path) -> OrgPorts:
        resolved = Path(root).expanduser().resolve()
        if not (resolved / "ORG.md").is_file():
            raise OrgError(f"not an organization (no ORG.md): {resolved}")
        return RuntimePorts(open_runtime(resolved))

    def initialize(self, root: Path, mission: str, config: Mapping[str, object] | None) -> None:
        resolved = Path(root).expanduser().resolve()
        open_runtime(resolved).org_initializer.init(resolved, mission, config)  # the ports of the new organization: it exists once ORG.md does


def provide(binding: OrgBindingPort, port: type[T]) -> Provider[T]:
    """The ``port`` of the organization the binding opens, asked for when the tool runs (an ``OrgError`` while there is none)."""
    return lambda: cast(OrgPorts, binding.get()).get(port)


class PatchPointSchedulerControl(SchedulerControl):
    """The control of the runtime, except that ``orgmcp.server.start_scheduler`` is looked up at the time of the call: the tests replace it (patch
    point of the flat module). Only the servers made through ``orgmcp.server`` have it. Deleted with that module (E3)."""

    def __init__(self, inner: SchedulerControl, root: Path) -> None:
        self._inner = inner
        self._root = root

    def start(self, max_runs: int | None = None, until_done: bool = False) -> int:
        shim, scheduler = sys.modules.get("orgmcp.server"), sys.modules.get("orgmcp.scheduler")
        patched = getattr(shim, "start_scheduler", None)
        if patched is None or scheduler is None or patched is getattr(scheduler, "start_scheduler", None):
            return self._inner.start(max_runs, until_done)
        from .facade import Org

        return cast(int, patched(Org(self._root), max_runs, until_done))

    def stop(self, wait: float = 15.0) -> str:
        return self._inner.stop(wait)


def plan_time_parts() -> PlanParts:
    """The plan side of ``blueprint`` for the time before the organization exists: the defaults of an organization, no name taken. It needs nothing of
    a root, so it is made over a builder of the shared providers that is bound to no organization."""
    from ..blueprint import BlueprintLoader, BlueprintValidator, RoleLibrary
    from ..blueprint._access import PolicyAccessReport
    from ..blueprint._assembly import plan_parts
    from ..blueprint._budgeting import BudgetPlanner
    from ..blueprint._org import NoOrgContext
    from ..blueprint._pathcheck import RootedPathChecker
    from ..blueprint._resolver import AgentResolver
    from ..blueprint._roots import EnvironmentWorkspaceRoots
    from ..kiro import ConfinementPolicy
    from ..services import ContractNormalizer
    from . import wire_blueprint

    b = Builder(Path("."), None, providers())
    environment = b.get(Environment)
    paths = RootedPathChecker(environment)
    return plan_parts(
        b.get(BlueprintLoader), b.get(BlueprintValidator), AgentResolver(b.get(RoleLibrary), paths),
        EnvironmentWorkspaceRoots(environment, wire_blueprint.temp_dir), BudgetPlanner(), PolicyAccessReport(b.get(ConfinementPolicy)),
        b.get(ContractNormalizer), NoOrgContext(),
    )


class CachedPlanTime:
    """``plan_time_parts``, made on the first proposal."""

    def __init__(self) -> None:
        self._parts: PlanParts | None = None

    def get(self) -> PlanParts:
        if self._parts is None:
            self._parts = plan_time_parts()
        return self._parts


def server_factory(binding: OrgBindingPort, patch_points: bool = False) -> McpServerFactory:
    """The factory of the servers bound to ``binding``. ``patch_points``: the servers of ``orgmcp.server`` (see the module docstring)."""
    from ..access import ToolNaming
    from ..agents import AgentDirectory, CharterReader
    from ..attention import OpenWork, WaitingOnUser
    from ..blueprint import BlueprintApplier, BlueprintExamples, BlueprintLoader, PlanIdentity, PlanRenderer
    from ..blueprint._examples import TemplateBlueprintExamples
    from ..blueprint._files import FsTextFiles
    from ..blueprint._identity import HashPlanIdentity
    from ..blueprint._loader import YamlBlueprintLoader
    from ..budget import BudgetQuery, BudgetReclaimer
    from ..daemon import SchedulerStatus
    from ..dispatch import MessageSender, TaskAssigner, TaskReporter
    from ..health import HealthAnalyzer, HealthRenderer
    from ..hierarchy import Hiring, Retirement
    from ..kernel import OrgLayout
    from ..mail import BatchStore, MailboxReader
    from ..mcp_server._factory import GroupedServerFactory
    from ..mcp_server._instructions import InstructionText
    from ..mcp_server._recorder import BatchCallTrace, ToolCallRecorder
    from ..mcp_server._tools_blueprint import (
        ApprovedPlanApplication,
        BindingPlanTarget,
        BlueprintTools,
        EnvironmentExampleLocation,
        RenderedPlanProposal,
        TemplateExampleText,
    )
    from ..mcp_server._tools_files import FileTools
    from ..mcp_server._tools_hiring import HiringTools
    from ..mcp_server._tools_identity import IdentityTools
    from ..mcp_server._tools_notes import NoteTools
    from ..mcp_server._tools_observe import ObservabilityTools
    from ..mcp_server._tools_progress import ProgressTools
    from ..mcp_server._tools_scheduler import SchedulerTools
    from ..mcp_server._tools_services import DirectoryServiceRoles, ServiceTools
    from ..mcp_server._tools_setup import RootSetupTools
    from ..mcp_server._tools_status import StatusTools
    from ..mcp_server._tools_tasks import TaskTools
    from ..observability import ObservabilityText
    from ..orgfiles import OrgFileReader, OrgFileWriter
    from ..overview import OrgTree
    from ..progress import ProgressReporter
    from ..prompts import Whoami
    from ..reflection import ServiceReports
    from ..services import ServiceCatalog, ServiceCommands, ServiceHints
    from ..telemetry._summarize import JsonArgumentSummarizer
    from ..traces import TraceLookup

    def of(port: type[T]) -> Provider[T]:
        return provide(binding, port)

    resources, environment = process_resources(), OsEnvironment()
    plan_time = CachedPlanTime()
    text = InstructionText(binding)  # the instructions, and the setup state
    directory = of(AgentDirectory)

    def control() -> SchedulerControl:
        real = of(SchedulerControl)()
        located = binding.location()
        return PatchPointSchedulerControl(real, located) if patch_points and located is not None else real

    def renderer() -> PlanRenderer:
        return of(PlanRenderer)() if binding.peek() is not None else plan_time.get().renderer

    loader: Provider[BlueprintLoader] = lambda: YamlBlueprintLoader(FsTextFiles())  # (no organization is needed to read a blueprint)
    identity: Provider[PlanIdentity] = lambda: HashPlanIdentity()
    examples: Provider[BlueprintExamples] = lambda: TemplateBlueprintExamples()

    common = [
        IdentityTools(text, of(Whoami), of(SchedulerStatus), of(BatchStore), of(MailboxReader)),
        TaskTools(of(TaskAssigner), of(TaskReporter), of(BudgetQuery), of(MailboxReader), of(ServiceHints)),
        NoteTools(of(MessageSender), of(BudgetQuery), of(BudgetReclaimer)),
        HiringTools(of(Hiring), of(Retirement)),
        FileTools(of(ToolNaming), of(OrgFileReader), of(OrgFileWriter), of(OrgLayout)),
        StatusTools(text, of(OrgTree), of(SchedulerStatus), directory, of(HealthAnalyzer), of(HealthRenderer)),
        ServiceTools(DirectoryServiceRoles(text, directory, of(CharterReader), of(ServiceCatalog)), of(ServiceReports), of(ServiceCommands), of(BudgetQuery)),
    ]
    root_only = [
        ObservabilityTools(of(ObservabilityText)),
        RootSetupTools(binding),
        SchedulerTools(control, of(SchedulerStatus), of(WaitingOnUser), of(OpenWork), of(OrgLayout)),
        BlueprintTools(
            TemplateExampleText(examples, EnvironmentExampleLocation(environment, binding)),
            RenderedPlanProposal(loader, renderer, BindingPlanTarget(binding, directory)),
            ApprovedPlanApplication(text, loader, identity, of(BlueprintApplier), of(SchedulerStatus), of(OrgLayout)),
        ),
        ProgressTools(text, of(ProgressReporter)),
    ]
    recorder = ToolCallRecorder(
        binding, resources.event_sinks, resources.trace_scope, JsonArgumentSummarizer(),
        BatchCallTrace(text, of(TraceLookup), directory, of(MailboxReader)),
    )
    return GroupedServerFactory(binding, directory, text, recorder, common, root_only)


class WiredServerFactories(ServerFactories):
    def __init__(self, patch_points: bool = False) -> None:
        self._patch_points = patch_points

    def factory_for(self, binding: OrgBindingPort) -> McpServerFactory:
        return server_factory(binding, self._patch_points)


def binding_resolver(bindings: BindingFactory | None = None, opener: OrgOpener | None = None) -> BindingResolver:
    """The resolver of the environment of this process (``ORG_AGENT``, ``ORG_REQUIRE_AGENT``, ``ORG_ROOT``, the working directory)."""
    from ..mcp_server._resolver import EnvBindingResolver

    opener = opener or RuntimeOrgOpener()
    return EnvBindingResolver(OsEnvironment(), os_locator(), opener, bindings or OpenerBindings(opener))


def mcp_server_runner(patch_points: bool = False) -> McpServerRunner:
    """The process that serves the identity of the environment over stdio (what ``orgmcp mcp`` runs)."""
    from ..mcp_server._serve import StdioMcpRunner

    return StdioMcpRunner(process_resources().process_label, binding_resolver(), WiredServerFactories(patch_points))


def serve() -> None:
    mcp_server_runner().run()


# ------------------------------------------------------------------------------------------------------ the module orgmcp.server (shim)


class LegacyOrgBinding(OrgBinding):
    """``OrgBinding(root, org=None, pinned=False)``: the constructor of the flat module, over an ``Org`` (or none) instead of an opener, and a
    ``create`` that returns the ``Org`` it made. Deleted with ``orgmcp.server`` (E3)."""

    def __init__(self, root: Path | None, org: Org | None = None, pinned: bool = False, *, ports: OrgPorts | None = None) -> None:
        super().__init__(root, RuntimeOrgOpener(), RuntimePorts(org.runtime) if org is not None else ports, pinned)

    def create(self, mission: str, default_model: str | None = None, path: str | None = None) -> Org:  # type: ignore[override]
        super().create(mission, default_model, path)
        from .facade import Org

        return Org(cast(Path, self.root))


class LegacyBindings(BindingFactory):
    def bind(self, root: Path | None, ports: OrgPorts | None = None, pinned: bool = False) -> LegacyOrgBinding:
        return LegacyOrgBinding(root, None, pinned, ports=ports)


def legacy_build_server(org: Org | OrgBindingPort, me: str) -> FastMCP:
    """``build_server(org, me)``: the MCP server for ``me``. ``org``: an ``Org``, or a binding (root only: it may not exist yet)."""
    binding = org if isinstance(org, OrgBindingPort) else LegacyOrgBinding(org.root, org)
    return cast("FastMCP", server_factory(binding, patch_points=True).build(me))


def legacy_resolve_binding() -> tuple[LegacyOrgBinding, str]:
    """``resolve_binding()``: the binding of the environment, and who it acts as."""
    binding, me = binding_resolver(LegacyBindings()).resolve()
    return cast(LegacyOrgBinding, binding), me
