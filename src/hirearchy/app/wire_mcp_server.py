"""The MCP server over the ports of the organization its binding opens (ARCHITECTURE.md 6.3): the factory of servers, the resolver of the binding, the runner.

The server is not a port of the runtime (``NOT_A_FIELD`` of ``fields_mcp_server``): a server is made per binding and per identity. The binding holds an
*opener* (``RuntimeOrgOpener``), not a runtime, because the organization may not exist yet (setup mode); every tool group receives ``Provider`` thunks
of the narrow ports of the features, which ask the binding at tool-call time, so a server opens the runtime of its organization on its first tool call.
Process-scope objects (the sinks of the events, the trace scope, the process label) need no organization and are the process's own.

Heavy modules (the MCP framework, the tool groups) are imported when a server is made, not when the application package is loaded: every command of the
command line opens a runtime, and none of them but ``hirearchy mcp`` needs a server.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast

from ..daemon import SchedulerControl
from ..kernel import Environment, OrgError, Provider
from ..kernel._system import OsEnvironment
from ..mcp_server import BindingResolver, McpServerFactory, McpServerRunner, OrgBindingPort
from ..mcp_server._binding import OpenerBindings
from ..mcp_server._instructions import DS_STORE, INSTRUCTIONS, ROOT_INSTRUCTIONS
from ..mcp_server._ports import BindingFactory, InstalledSkill, OrgOpener, OrgPorts, ServerFactories
from . import wire_skill
from ._builder import Builder
from .wire_locator import os_locator
from .wire_stalls import RuntimePorts
from .wiring import open_runtime, process_resources, providers

if TYPE_CHECKING:
    from ..blueprint._assembly import PlanParts

T = TypeVar("T")

__all__ = [
    "DS_STORE", "INSTRUCTIONS", "ROOT_INSTRUCTIONS", "PackagedInstalledSkill", "RuntimeOrgOpener", "WiredServerFactories", "binding_resolver", "mcp_server_runner", "register",
    "serve", "server_factory",
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


class PackagedInstalledSkill(InstalledSkill):
    """The skill installed under the home of ``environment`` against the one this install ships (``SkillCheck``). It needs no organization, because in
    setup mode none is bound and the first ``whoami`` of root is already there."""

    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def stale(self) -> Path | None:
        return wire_skill.skill_check(self._environment).stale()


def server_factory(binding: OrgBindingPort, scheduler_control: Callable[[SchedulerControl], SchedulerControl] | None = None) -> McpServerFactory:
    """The factory of the servers bound to ``binding``. ``scheduler_control``: wraps the control of the organization the ``start`` and ``stop`` tools use
    (the tests give a fake starter through it)."""
    from ..access import ModelFloorAudit, ToolNaming
    from ..agents import AgentDirectory, CharterReader
    from ..attention import OpenWork, WaitingOnUser
    from ..blueprint import BlueprintApplier, BlueprintExamples, BlueprintLoader, ExtensionApplying, PlanIdentity, PlanRenderer
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
    from ..mcp_server._root_structure import RootStructureGuard
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
    from ..mcp_server._tools_quality import QualityTools
    from ..mcp_server._tools_scheduler import SchedulerTools
    from ..mcp_server._tools_services import DirectoryServiceRoles, ServiceTools
    from ..mcp_server._tools_setup import RootSetupTools
    from ..mcp_server._tools_status import StatusTools
    from ..mcp_server._tools_tasks import TaskTools
    from ..observability import ObservabilityText
    from ..orgfiles import OrgFileReader, OrgFileWriter
    from ..overview import OrgTree
    from ..progress import ProgressReporter, QualityReport
    from ..prompts import Whoami
    from ..reflection import DeliverableChecks, ServiceReports, ServiceSteps
    from ..services import ServiceCatalog, ServiceCommands, ServiceEvidence, ServiceHints
    from ..settings import OrgSettings
    from ..telemetry._summarize import JsonArgumentSummarizer
    from ..traces import TraceLookup

    def of(port: type[T]) -> Provider[T]:
        return provide(binding, port)

    resources, environment = process_resources(), OsEnvironment()
    structure = RootStructureGuard(of(ServiceCatalog), of(OrgFileWriter), of(OrgSettings), of(OrgLayout))  # root's structural calls over MCP are refused in favour of the extension (design 13)
    plan_time = CachedPlanTime()
    text = InstructionText(binding)  # the instructions, and the setup state
    directory = of(AgentDirectory)
    installed_skill = PackagedInstalledSkill(environment)

    def control() -> SchedulerControl:
        real = of(SchedulerControl)()
        return scheduler_control(real) if scheduler_control is not None else real

    def renderer() -> PlanRenderer:
        return of(PlanRenderer)() if binding.peek() is not None else plan_time.get().renderer

    loader: Provider[BlueprintLoader] = lambda: YamlBlueprintLoader(FsTextFiles())  # (no organization is needed to read a blueprint)
    identity: Provider[PlanIdentity] = lambda: HashPlanIdentity()
    examples: Provider[BlueprintExamples] = lambda: TemplateBlueprintExamples()

    common = [
        IdentityTools(
            text, of(Whoami), of(SchedulerStatus), of(BatchStore), of(MailboxReader), installed_skill, of(DeliverableChecks), of(ModelFloorAudit),
        ),
        TaskTools(of(TaskAssigner), of(TaskReporter), of(BudgetQuery), of(MailboxReader), of(ServiceHints)),
        NoteTools(of(MessageSender), of(BudgetQuery), of(BudgetReclaimer)),
        HiringTools(of(Hiring), of(Retirement), of(ServiceCatalog), of(ServiceEvidence), structure),
        FileTools(of(ToolNaming), of(OrgFileReader), of(OrgFileWriter), of(OrgLayout), structure),
        StatusTools(
            text, of(OrgTree), of(SchedulerStatus), directory, of(HealthAnalyzer), of(HealthRenderer), installed_skill, of(DeliverableChecks),
            of(ModelFloorAudit),
        ),
        ServiceTools(
            DirectoryServiceRoles(text, directory, of(CharterReader), of(ServiceCatalog)), of(ServiceReports), of(ServiceCommands), of(BudgetQuery),
            of(ServiceSteps), structure,
        ),
    ]
    root_only = [
        ObservabilityTools(of(ObservabilityText)),
        RootSetupTools(binding),
        SchedulerTools(control, of(SchedulerStatus), of(WaitingOnUser), of(OpenWork), of(OrgLayout)),
        BlueprintTools(
            TemplateExampleText(examples, EnvironmentExampleLocation(environment, binding)),
            RenderedPlanProposal(loader, renderer, BindingPlanTarget(binding, directory)),
            ApprovedPlanApplication(text, loader, identity, of(BlueprintApplier), of(SchedulerStatus), of(OrgLayout), of(ExtensionApplying)),
        ),
        ProgressTools(text, of(ProgressReporter)),
        QualityTools(text, of(QualityReport)),
    ]
    recorder = ToolCallRecorder(
        binding, resources.event_sinks, resources.trace_scope, JsonArgumentSummarizer(),
        BatchCallTrace(text, of(TraceLookup), directory, of(MailboxReader)),
    )
    return GroupedServerFactory(binding, directory, text, recorder, common, root_only)


class WiredServerFactories(ServerFactories):
    def factory_for(self, binding: OrgBindingPort) -> McpServerFactory:
        return server_factory(binding)


def binding_resolver(bindings: BindingFactory | None = None, opener: OrgOpener | None = None) -> BindingResolver:
    """The resolver of the environment of this process (``ORG_AGENT``, ``ORG_REQUIRE_AGENT``, ``ORG_ROOT``, the working directory)."""
    from ..mcp_server._resolver import EnvBindingResolver

    opener = opener or RuntimeOrgOpener()
    return EnvBindingResolver(OsEnvironment(), os_locator(), opener, bindings or OpenerBindings(opener))


def mcp_server_runner() -> McpServerRunner:
    """The process that serves the identity of the environment over stdio (what ``hirearchy mcp`` runs)."""
    from ..mcp_server._serve import StdioMcpRunner

    return StdioMcpRunner(process_resources().process_label, binding_resolver(), WiredServerFactories())


def serve() -> None:
    mcp_server_runner().run()
