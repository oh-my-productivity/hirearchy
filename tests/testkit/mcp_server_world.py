"""Servers of ``mcp_server`` for the tests that run the tools over a real organization: through the composition root.

``build_server(org, me)`` / ``resolve_binding()`` / ``OrgBinding(root)`` have the shapes the tests used when they imported them from the old ``orgmcp.server``;
they are made by ``orgmcp.app.wire_mcp_server`` (``server_factory``, ``binding_resolver``, ``RuntimeOrgOpener``). ``StartRecorder`` stands for the old
patch point ``orgmcp.server.start_scheduler``: a fake starter that the server's ``start`` tool calls instead of the daemon's.

The rest are the old names that the tool tests read besides the server, kept so that the assertion lines of the tests stay as they were, over the new API:
``skill_source()``, ``telemetry.reset()`` / ``.summarize_args()``, ``services.read_playbook()`` / ``.cases()`` ..., ``blueprint.validate()`` / ``.plan_id()`` ...
(the process resources and the ports of a runtime), ``describe_scheduler`` / ``describe_progress`` and ``serve_until_done`` (a scheduler over a stand-in agent).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from orgmcp.app import wire_kiro, wire_scheduler, wire_skill, wiring
from orgmcp.app import wire_mcp_server as wire
from orgmcp.app.wire_cli import run_cli as main  # noqa: F401 - the command line of the composition root (``orgmcp.cli.main``)
from orgmcp.app.wire_stalls import RuntimePorts
from orgmcp.blueprint import EXAMPLE_KINDS, errors
from orgmcp.blueprint._org import NoOrgContext, RuntimeOrgContext
from orgmcp.blueprint._pathcheck import RootedPathChecker
from orgmcp.blueprint._plan_texts import PLAN_DRAFT_HEADING, PLAN_END, PLAN_HEADING
from orgmcp.blueprint._resolver import AgentResolver
from orgmcp.core import Org
from orgmcp.daemon import SchedulerControl
from orgmcp.kernel import OrgPaths
from orgmcp.kernel._system import FsAtomicWriter, SystemClock
from orgmcp.kiro import RunCommand, RunCommandBuilder
from orgmcp.kiro._profiles import FsProfileStore
from orgmcp.kiro._provisioner import OrgProfileProvisioner
from orgmcp.mcp_server import OrgBindingPort
from orgmcp.mcp_server._binding import OrgBinding as _OrgBinding
from orgmcp.mcp_server._ports import BindingFactory, OrgPorts
from orgmcp.reflection import stats_by_version
from orgmcp.scheduler._ports import Console
from orgmcp.scheduler._run import LoopState
from orgmcp.skill._source import PackagedSkillSource
from orgmcp.telemetry._summarize import JsonArgumentSummarizer

NO_ORG = Path("/nonexistent/orgmcp-no-org")  # a root nobody opens: the runtime of "no organization yet"
Starter = Callable[[int | None, bool], int]


class StartRecorder(SchedulerControl):
    """The control a server's ``start`` tool uses: ``starter(max_runs, until_done) -> pid`` when one is set, else the control of the organization."""

    def __init__(self) -> None:
        self.starter: Starter | None = None
        self._inner: SchedulerControl | None = None

    def wrap(self, inner: SchedulerControl) -> SchedulerControl:
        self._inner = inner
        return self

    def use(self, starter: Starter) -> None:
        self.starter = starter

    def start(self, max_runs: int | None = None, until_done: bool = False) -> int:
        if self.starter is not None:
            return self.starter(max_runs, until_done)
        assert self._inner is not None
        return self._inner.start(max_runs, until_done)

    def stop(self, wait: float = 15.0) -> str:
        assert self._inner is not None
        return self._inner.stop(wait)


class OrgBinding(_OrgBinding):
    """``OrgBinding(root, org=None, pinned=False)``: a binding over an ``Org`` that exists (or over a root that may not); ``create`` returns the ``Org`` it made."""

    def __init__(self, root: Path | None, org: Any = None, pinned: bool = False, *, ports: OrgPorts | None = None) -> None:
        super().__init__(root, wire.RuntimeOrgOpener(), RuntimePorts(org.runtime) if org is not None else ports, pinned)

    def create(self, mission: str, default_model: str | None = None, path: str | None = None) -> Any:
        super().create(mission, default_model, path)
        return Org(self.root)


class _Bindings(BindingFactory):
    def bind(self, root: Path | None, ports: OrgPorts | None = None, pinned: bool = False) -> OrgBinding:
        return OrgBinding(root, None, pinned, ports=ports)


def build_server(org: Any, me: str, starts: StartRecorder | None = None) -> Any:
    """The MCP server for ``me``. ``org``: an ``Org``, or a binding (a root only: the organization may not exist yet)."""
    binding = org if isinstance(org, OrgBindingPort) else OrgBinding(org.root, org)
    return wire.server_factory(binding, scheduler_control=starts.wrap if starts is not None else None).build(me)


def resolve_binding() -> tuple[OrgBindingPort, str]:
    """The binding of the environment (``ORG_ROOT``, ``ORG_AGENT``, ``ORG_REQUIRE_AGENT``), and who it acts as."""
    return wire.binding_resolver(_Bindings()).resolve()


def ensure_kiro_profile(tools: list[str], agents_dir: Path, *, org: Any) -> str:
    """The profile of ``org`` written into ``agents_dir`` (what ``scheduler.ensure_kiro_profile`` did), over the provisioner of ``kiro``."""
    store = FsProfileStore(lambda: Path(agents_dir), FsAtomicWriter())
    return OrgProfileProvisioner(OrgPaths(org.root), store, wire_kiro.confinement_policy(), wire_kiro.mcp_locator()).ensure_profile(tools)


# ------------------------------------------------------------------------------ the status lines and a scheduler over a stand-in agent


def describe_scheduler(org: Any) -> str:
    return org.runtime.scheduler_status.describe()


def describe_progress(org: Any, task_id: str | None = None, wait_seconds: int = 0) -> str:
    return org.runtime.progress_reporter.describe_progress(task_id, wait_seconds)


class _Silent(Console):
    def say(self, line: str) -> None:
        pass


class _StandInAgent(RunCommandBuilder):
    """The command of a run is the stand-in agent script (``testkit.FAKE_AGENT``) in ``mode``, run in the directory of the agent."""

    def __init__(self, org: Any, script: str, mode: str) -> None:
        self._org, self._script, self._mode = org, script, mode

    def build(self, addr: str, prompt: str) -> RunCommand:
        env = {**os.environ, "ORG_ROOT": str(self._org.root), "ORG_AGENT": addr, "FAKE_MODE": self._mode}
        return RunCommand((sys.executable, self._script), self._org.dir(addr), env)


def serve_until_done(org: Any, script: str, mode: str = "work") -> None:
    """The scheduler of ``org`` runs the stand-in agent ``script`` until the work is done (what ``Scheduler(org, runner).serve(until_done=True)`` did)."""
    loop = wire_scheduler.loop_of(org.runtime, _StandInAgent(org, script, mode), _Silent(), SystemClock(), LoopState())
    loop.serve(until_done=True)


# ------------------------------------------------------------------------------ the old names of the modules the tool tests read, over the new API


def skill_source() -> Path:
    """The SKILL.md that ships with this install (what ``orgmcp.skill.skill_source`` answered)."""
    return PackagedSkillSource(wire_skill.package_dir()).path()


class _Telemetry:
    """``orgmcp.telemetry.reset`` / ``summarize_args``: the process resources of the composition root, and the summarizer of the arguments."""

    @staticmethod
    def reset() -> None:
        wiring.process_resources().reset()

    @staticmethod
    def summarize_args(arguments: dict[str, Any]) -> Any:
        return JsonArgumentSummarizer().summarize(arguments)


telemetry = _Telemetry()


class _Services:
    """``orgmcp.services`` / ``orgmcp.reflection`` reads of an organization: the ports of its runtime."""

    stats_by_version = staticmethod(stats_by_version)

    @staticmethod
    def read_playbook(org: Any, owner: str, name: str) -> Any:
        return org.runtime.service_catalog.read_playbook(owner, name)

    @staticmethod
    def services_text(org: Any, actor: str) -> str:
        return org.runtime.service_reports.services_text(actor)

    @staticmethod
    def cases(org: Any, owner: str, name: str) -> Any:
        return org.runtime.case_history.cases(owner, name)

    @staticmethod
    def reflection_digest(org: Any, owner: str, name: str) -> Any:
        return org.runtime.reflection_digest.reflection_digest(owner, name)


services = _Services()


class _Blueprint:
    """``orgmcp.blueprint`` as the tool tests called it (``validate``, ``load_text``, ``plan_id`` ...), over the ports of a runtime of no organization.

    The blueprint tests have the fuller world (``testkit.blueprint_world``); these tests use five functions and the plan constants."""

    PLAN_HEADING = PLAN_HEADING
    PLAN_DRAFT_HEADING = PLAN_DRAFT_HEADING
    PLAN_END = PLAN_END
    KINDS = EXAMPLE_KINDS
    errors = staticmethod(errors)

    @staticmethod
    def _runtime() -> Any:
        return wiring.open_runtime(NO_ORG)

    def load_text(self, text: str) -> Any:
        return self._runtime().blueprint_loader.load_text(text)

    def validate(self, bp: Any, *, org: Any = None, allowed_roots: Any = None) -> Any:
        runtime = org.runtime if org is not None else self._runtime()
        return runtime.blueprint_validator.validate(bp, org_exists=org is not None, allowed_roots=allowed_roots)

    def plan_id(self, bp: Any) -> str:
        return self._runtime().plan_identity.plan_id(bp)

    def _resolve(self, bp: Any, org: Any, roots: Any, issues: Any) -> Any:
        runtime = self._runtime()
        context = RuntimeOrgContext(runtime.settings, runtime.agents, runtime.service_catalog, runtime.paths) if org is not None else NoOrgContext()
        return AgentResolver(runtime.role_library, RootedPathChecker(runtime.environment)).resolve(bp, context, roots, issues)


blueprint = _Blueprint()
