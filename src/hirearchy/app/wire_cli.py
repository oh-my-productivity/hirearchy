"""The command line over the ports of the organization it opens (ARCHITECTURE.md 6.3): the commands, the session, the record of a command, the launchers.

The program is not a port of the runtime (``NOT_A_FIELD`` of ``fields_cli``): the organization a command works on is named by its arguments, so the commands
are built before any runtime exists and reach the features through ``Provider`` thunks that ask the organization the session opened last. Process-scope objects
(the sinks of the events, the name of the process, the clock) need no organization and are the process's own.

What the other entry points do for ``run``, ``mcp`` and ``dash`` is behind the ports of ``cli._ports``: ``LoopSchedulerRunner`` makes the scheduler's loop over the
runtime and runs it (one pass, or until it is told to stop), ``LazyMcpRunner`` serves the MCP tools, ``LazyDashboardRunner`` starts the full-screen dashboard. The two
heavy ones are imported when they are used: no other command, and not the start of the program, imports the MCP framework or Textual.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn, TypeVar

from ..agents import AgentDirectory
from ..blueprint import BlueprintApplier, BlueprintLoader, BlueprintValidator, PlanRenderer, RoleLibrary
from ..blueprint._access import PolicyAccessReport
from ..blueprint._assembly import plan_parts
from ..blueprint._budgeting import BudgetPlanner
from ..blueprint._org import NoOrgContext, PresentOrAbsentOrg
from ..blueprint._pathcheck import RootedPathChecker
from ..blueprint._resolver import AgentResolver
from ..blueprint._roots import EnvironmentWorkspaceRoots
from ..blueprint._service_rules import ServiceBlueprintRules
from ..blueprint._validator import RuleBlueprintValidator
from ..bootstrap import OrgInitializer
from ..cli import CliApp
from ..cli._app import ArgparseCliApp
from ..cli._args import AtFileText
from ..cli._commands_blueprint import ApplyCommand, PlanCommand
from ..cli._commands_obs import CheckCommand, EventsCommand, MetricsCommand, NowCommand, ObsCommand, TraceCommand
from ..cli._commands_ops import (
    InstallSkillCommand,
    KiroProfileCommand,
    McpCommand,
    ReviewCommand,
    RunCommand,
    UpgradeRulesCommand,
)
from ..cli._commands_org import HireCommand, InboxCommand, InitCommand, ResumeCommand, SendCommand, TaskCommand
from ..cli._commands_services import (
    DefineServiceCommand,
    FeedbackCommand,
    RequestCommand,
    RetireServiceCommand,
    ServicesCommand,
)
from ..cli._commands_views import DashCommand, HealthCommand, ProgressCommand, StatusCommand
from ..cli._ports import (
    Command,
    DashboardRunner,
    EventTail,
    EventTails,
    JsonDump,
    McpRunner,
    OrgOpener,
    OrgPorts,
    OrgSession,
    Output,
    SchedulerRunner,
    Terminal,
)
from ..cli._record import EventCommandRecorder
from ..cli._session import AnnouncingOrgSession
from ..daemon import REFUSED_START, SchedulerStatus
from ..dashdata import SnapshotRenderer
from ..dispatch import MessageSender, TaskAssigner
from ..eligibility import FailureCounter, PauseStore
from ..eventlog import EventFollower, EventFollowers, EventReader
from ..health import HealthAnalyzer, HealthRenderer
from ..hierarchy import Hiring
from ..kernel import Clock, Environment, JsonObject, OrgError, Provider
from ..kernel._system import SystemClock
from ..kiro import ConfinementPolicy, KiroPlaces, McpServerLocator, ProfileProvisioner, RuntimeReadiness
from ..mail import BatchStore, MailboxReader, TaskQuery
from ..observability import (
    EventQueries,
    IntegrityChecks,
    MetricQueries,
    NowQueries,
    ObservabilityRenderer,
    TraceQueries,
)
from ..observability._util import matcher, plain
from ..overview import OrgTree
from ..progress import ProgressReporter
from ..reflection import ServiceReports, ServiceSteps
from ..review import HealthReviewer
from ..scheduler._ports import Console
from ..scheduler._run import LoopState
from ..services import ContractNormalizer, ServiceCatalog, ServiceCommands
from ..skill import SkillInstaller
from ..snapshots import OrgSnapshotter
from ..upgrade import RulesUpgrader
from . import wire_blueprint, wire_dashboard, wire_dashdata, wire_kiro
from ._builder import Builder
from .runtime import OrgRuntime
from .wire_locator import os_locator
from .wire_mcp_server import mcp_server_runner
from .wire_scheduler import loop_of
from .wire_stalls import RuntimePorts
from .wiring import open_runtime, process_resources, providers

T = TypeVar("T")


def register(b: Builder) -> None:
    """The command line has no port of its own (see the module docstring)."""


# ------------------------------------------------------------------------------------------------------------ the process


class StandardOutput(Output):
    """The standard output and error of this process, looked up at each call (a test redirects them)."""

    def say(self, text: str = "", flush: bool = False) -> None:
        print(text, flush=flush)

    def write(self, text: str) -> None:
        print(text, end="")

    def warn(self, text: str) -> None:
        print(text, file=sys.stderr, flush=True)


class StandardTerminal(Terminal):
    def is_interactive(self) -> bool:
        return sys.stdin.isatty() and sys.stdout.isatty()

    def stdout_is_tty(self) -> bool:
        return sys.stdout.isatty()


class PlainJson(JsonDump):
    """Indented JSON of a view: datetimes as ISO text, tuples and sets as lists, paths as text (what the observability calls ``plain``)."""

    def dump(self, data: object) -> str:
        return json.dumps(plain(data), indent=2, default=str)


# ------------------------------------------------------------------------------------------------------ the organization


class RuntimeOrgPorts(OrgPorts):
    """An organization opened with ``open_runtime``: each port is the field of its runtime that has its type."""

    def __init__(self, runtime: OrgRuntime) -> None:
        self._ports = RuntimePorts(runtime)
        self._root = runtime.root

    @property
    def root(self) -> Path:
        return self._root

    def get(self, port: type[T]) -> T:
        return self._ports.get(port)


class RuntimeOrgOpener(OrgOpener):
    def open(self, root: Path) -> OrgPorts:
        if not (root / "ORG.md").is_file():
            raise OrgError(f"not an organization (no ORG.md): {root}")
        return RuntimeOrgPorts(open_runtime(root))

    def prepare(self, root: Path) -> OrgPorts:
        return RuntimeOrgPorts(open_runtime(root))


def of(session: OrgSession, port: type[T]) -> Provider[T]:
    """The ``port`` of the organization the session opened last, asked for when the command uses it."""
    return lambda: session.ports().get(port)


class ClockedEventTail(EventTail):
    """A follower of the event files, polled at the time of the clock of the runtime."""

    def __init__(self, follower: EventFollower, clock: Clock) -> None:
        self._follower = follower
        self._clock = clock

    def poll(self) -> list[JsonObject]:
        return self._follower.poll(True, self._clock.now())


class RuntimeEventTails(EventTails):
    """The tail of the event files of the opened organization, started by the clock of its runtime."""

    def __init__(self, ports: OrgPorts) -> None:
        self._ports = ports

    def follow(self, agent: str | None, kind: str | None, trace: str | None, errors: bool) -> EventTail:
        clock = self._ports.get(Clock)
        return ClockedEventTail(self._ports.get(EventFollowers).follow(matcher(agent, kind, trace, errors), clock.now()), clock)

    def any(self) -> bool:
        return bool(self._ports.get(EventReader).files())


# --------------------------------------------------------------------------------------------- the other entry points


class OutputConsole(Console):
    """What the scheduler says is what the command line prints."""

    def __init__(self, out: Output) -> None:
        self._out = out

    def say(self, line: str) -> None:
        self._out.say(line)


class LoopSchedulerRunner(SchedulerRunner):
    """The scheduler's loop over the runtime of the organization, with kiro-cli (or ``--kiro BIN``) as the agent runner."""

    def __init__(self, out: Output, cadence: Clock) -> None:
        self._out = out
        self._cadence = cadence

    def run(self, root: Path, kiro_bin: str, once: bool, until_idle: bool, until_done: bool, max_runs: int | None) -> None:
        runtime = open_runtime(root)
        problem = runtime.runtime_readiness.check(kiro_bin)  # before anything else, also for ``--max-runs 0`` and ``--once``: no run is made unready
        if problem is not None:
            self._refuse(runtime, problem)
        commands = wire_kiro.run_command_builder(runtime, kiro_bin, runtime.profile_provisioner)
        loop = loop_of(runtime, commands, OutputConsole(self._out), self._cadence, LoopState())
        if once:
            loop.run_once(max_runs)
        else:
            loop.serve(until_idle=until_idle, max_runs=max_runs, until_done=until_done)

    @staticmethod
    def _refuse(runtime: OrgRuntime, problem: str) -> NoReturn:
        """Leave the refusal where ``status`` and ``progress`` read it (unless a scheduler is alive: its own status wins), then fail the start."""
        if runtime.scheduler_status.state().state == "stopped":
            runtime.ignore_list.ensure_runtime_files()  # as a claim does: the marker stays out of the snapshots of the organization
            runtime.exit_marker.write(f"{REFUSED_START}kiro-cli is not ready: {problem}")
        raise OrgError(f"kiro-cli is not ready, no run was started: {problem}")


class LazyMcpRunner(McpRunner):
    """Serves the MCP tools; the framework is imported only now."""

    def run(self) -> None:
        mcp_server_runner().run()


class LazyDashboardRunner(DashboardRunner):
    """Starts the full-screen dashboard; Textual is imported only now (``wire_dashboard.dashboard_launcher`` imports it when it makes the launcher)."""

    def run(self, root: Path, interval: float) -> None:
        wire_dashboard.dashboard_launcher().run_dashboard(Path(root), interval)


# ------------------------------------------------------------------------------------------------------- the blueprints


class PlanTime:
    """What checks and renders a blueprint before the organization exists: the defaults of an organization, no name taken."""

    def __init__(self) -> None:
        self._built: tuple[BlueprintValidator, PlanRenderer] | None = None

    def get(self) -> tuple[BlueprintValidator, PlanRenderer]:
        if self._built is None:
            self._built = self._make()
        return self._built

    @staticmethod
    def _make() -> tuple[BlueprintValidator, PlanRenderer]:
        b = Builder(Path("."), None, providers())  # (bound to no organization: only the shared providers are used)
        environment = b.get(Environment)
        paths, budgets = RootedPathChecker(environment), BudgetPlanner()
        resolver = AgentResolver(b.get(RoleLibrary), paths)
        roots = EnvironmentWorkspaceRoots(environment, wire_blueprint.temp_dir)
        access = PolicyAccessReport(b.get(ConfinementPolicy))
        normalizer = b.get(ContractNormalizer)
        none = NoOrgContext()
        validator = RuleBlueprintValidator(
            resolver, paths, budgets, access, ServiceBlueprintRules(normalizer, paths, budgets), roots, PresentOrAbsentOrg(none, none),
        )
        return validator, plan_parts(b.get(BlueprintLoader), validator, resolver, roots, budgets, access, normalizer, none).renderer


def validator_of(session: OrgSession, plan_time: PlanTime) -> Provider[BlueprintValidator]:
    def provide() -> BlueprintValidator:
        try:
            return session.ports().get(BlueprintValidator)
        except OrgError:
            return plan_time.get()[0]

    return provide


def renderer_of(session: OrgSession, plan_time: PlanTime) -> Provider[PlanRenderer]:
    def provide() -> PlanRenderer:
        try:
            return session.ports().get(PlanRenderer)
        except OrgError:
            return plan_time.get()[1]

    return provide


def snapshot_renderer_of(session: OrgSession) -> Provider[SnapshotRenderer]:
    """The text of ``dash --once``: from the runtime of the dashboard (lenient readers), not the strict one the other commands use."""
    return lambda: RuntimePorts(wire_dashdata.dashboard_runtime(session.ports().root)).get(SnapshotRenderer)


# ------------------------------------------------------------------------------------------------------------ the program


def commands_over(session: OrgSession, out: Output, terminal: Terminal, clock: Clock) -> Sequence[Command]:
    """Every command, in the order of the parser."""
    def get(port: type[T]) -> Provider[T]:
        return of(session, port)

    text, dump, plan_time = AtFileText(), PlainJson(), PlanTime()
    snapshots, commands = get(OrgSnapshotter), get(ServiceCommands)
    renderer = get(ObservabilityRenderer)
    unbound = Builder(Path("."), None, providers())  # (the skill, and the reading of a blueprint, need no organization)
    loader: Provider[BlueprintLoader] = lambda: unbound.get(BlueprintLoader)
    tails: Provider[EventTails] = lambda: RuntimeEventTails(session.ports())
    views = [
        NowCommand(session, get(NowQueries), renderer, dump, terminal, clock, out),
        TraceCommand(session, get(TraceQueries), renderer, dump, out),
        MetricsCommand(session, get(MetricQueries), renderer, dump, out),
        EventsCommand(session, get(EventQueries), renderer, tails, dump, clock, out),
    ]
    return [
        InitCommand(session, get(OrgInitializer), text, out),
        HireCommand(session, get(Hiring), snapshots, text, out),
        TaskCommand(session, get(TaskAssigner), snapshots, text, out),
        ServicesCommand(session, get(ServiceReports), out),
        DefineServiceCommand(session, commands, get(ServiceCatalog), get(ContractNormalizer), snapshots, text, out),
        RequestCommand(session, commands, snapshots, get(ServiceSteps), out),
        FeedbackCommand(session, commands, snapshots, out),
        RetireServiceCommand(session, commands, snapshots, out),
        PlanCommand(session, loader, validator_of(session, plan_time), renderer_of(session, plan_time), out),
        ApplyCommand(session, loader, get(BlueprintApplier), out),
        SendCommand(session, get(MessageSender), snapshots, text, out),
        StatusCommand(session, get(OrgTree), get(TaskQuery), get(SchedulerStatus), out),
        HealthCommand(session, get(HealthAnalyzer), get(HealthRenderer), out),
        ProgressCommand(session, get(ProgressReporter), out),
        UpgradeRulesCommand(session, get(RulesUpgrader), out),
        InstallSkillCommand(unbound.get(SkillInstaller), out),
        ReviewCommand(session, get(HealthReviewer), snapshots, out),
        InboxCommand(session, get(MailboxReader), get(BatchStore), out),
        ResumeCommand(session, get(AgentDirectory), get(PauseStore), get(FailureCounter), out),
        RunCommand(session, LoopSchedulerRunner(out, clock)),
        McpCommand(LazyMcpRunner()),
        DashCommand(session, snapshot_renderer_of(session), LazyDashboardRunner(), terminal, out),
        ObsCommand(views),
        CheckCommand(session, get(IntegrityChecks), renderer, dump, out),
        KiroProfileCommand(session, get(ProfileProvisioner), get(RuntimeReadiness), get(KiroPlaces), get(McpServerLocator), out),
    ]


def cli_app(clock: Clock | None = None) -> CliApp:
    """The command line of this process; ``clock`` is the one its commands wait and time by (default: the system's)."""
    out, clock = StandardOutput(), clock or SystemClock()
    session = AnnouncingOrgSession(os_locator(), RuntimeOrgOpener(), out)
    resources = process_resources()
    recorder = EventCommandRecorder(resources.event_sinks, session, clock)
    return ArgparseCliApp(commands_over(session, out, StandardTerminal(), clock), recorder, resources.process_label, clock, out)


def run_cli(argv: Sequence[str] | None = None, clock: Clock | None = None) -> None:
    """``hirearchy``: what the console script, ``python -m hirearchy`` and ``hirearchy.cli.main`` run (``clock``: see ``cli_app``)."""
    cli_app(clock).main(argv)
