"""The legacy surface of the scheduler: the module functions the callers and tests still use, and the ``Scheduler`` class.

The heartbeat - one fresh, short run of an agent whenever its inbox has messages, one agent at most once at a time, different agents in parallel, a run a
separate process (kiro-cli by default) whose orgmcp MCP server is bound to the agent via ORG_AGENT - is the ``HeartbeatLoop`` of ``_loop``, made from the
ports of a runtime by ``app.wire_scheduler.loop_of``. ``Scheduler`` is what is left of the old class: it is given an ``Org``, a runner, an output and a clock,
and hands every call to the loop that ``org.runtime`` makes (made again when the runtime is replaced under it). It goes with the legacy surface (E3).
"""

from __future__ import annotations

import importlib
import sys
import time
from collections.abc import Collection, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, cast

from ..attention import Waiting
from ..daemon import SchedulerState
from ..kernel import Clock
from ..kiro import RunCommand, RunCommandBuilder
from ..processes import ProcessTableError
from ._loop import HeartbeatLoop
from ._ports import Console
from ._run import LoopMemory, LoopState, RunCount, RunRecord, RunTable
from .api import SchedulerLoop

Run = RunRecord  # the old name of the data of a run in flight
Org = Any  # the facade: an entry point may not import it, so the legacy class takes whatever has a ``runtime`` (as the callers pass it)


def _wire(name: str) -> Any:
    """The composition root's module ``orgmcp.app.<name>``, looked up late: an entry point may not import ``orgmcp.app`` (the layers contract), and
    these legacy functions have no runtime to take their ports from. They go with the legacy surface (E3)."""
    return importlib.import_module(f"orgmcp.app.{name}")


wire_attention, wire_daemon, wire_kiro, wire_processes = _wire("wire_attention"), _wire("wire_daemon"), _wire("wire_kiro"), _wire("wire_processes")

# (org, agent address, prompt) -> (argv, cwd, env). The prompt is delivered on the process's stdin, not in argv.
Runner = Callable[[Org, str, str], tuple[list[str], Path, dict[str, str]]]

PROJECT_DIR = wire_kiro.project_dir()  # two levels above the package, as `Path(__file__).resolve().parents[2]` was
KIRO_AGENTS_DIR = Path.home() / ".kiro" / "agents"  # evaluated at import, as before; tests patch it (the wrappers read it at call time)


def _patched(name: str) -> Any:
    """The attribute ``name`` of the package ``orgmcp.scheduler`` as it is now: tests replace ``mcp_server_command``, ``file_confinement``,
    ``ensure_kiro_profile``, ``kiro_profile_name`` and ``KIRO_AGENTS_DIR`` there (the golden kiro tests do), and the code that reads them
    lives in this module."""
    return getattr(sys.modules["orgmcp.scheduler"], name)


# The kiro functions below are thin wrappers over `orgmcp.kiro` (B-kiro) until the scheduler is converted (D-sched-1): they stay module
# attributes because tests replace them (`mcp_server_command`, `file_confinement`, `ensure_kiro_profile`) and the settings above
# (`KIRO_AGENTS_DIR`), and each wrapper uses whatever is in force when it is called.


def mcp_server_command() -> dict[str, object]:
    """How kiro should start the orgmcp MCP server (prefer the venv's console script)."""
    return cast("dict[str, object]", wire_kiro.mcp_locator().command())


def kiro_profile_name(org_root: str | Path, tools: list[str]) -> str:
    """``orgmcp-<org-slug>-<6-char hash of the org root path>[-<tools>]``, lowercase ``[a-z0-9-]`` (see ``OrgProfileProvisioner``)."""
    return cast(str, wire_kiro.profile_name(Path(org_root), tools))


def file_confinement(
    org_root: Path, tools: list[str], workspace: Path | None, inputs: list[Path]
) -> tuple[list[str], dict[str, object]]:
    """(allowedTools, toolsSettings) that confine kiro's built-in ``read``/``write`` by path (see ``KiroConfinementPolicy``)."""
    return cast("tuple[list[str], dict[str, object]]", wire_kiro.confinement_policy().file_confinement(org_root, tools, workspace, inputs))


def ensure_kiro_profile(
    tools: list[str], agents_dir: Path | None = None, *, org: Org,
    workspace: Path | None = None, inputs: list[Path] | None = None, confine: bool = False,
) -> str:
    """Write the scheduler's profile for ``org`` into ``~/.kiro/agents`` (see ``OrgProfileProvisioner.ensure_profile``).

    The directory is resolved when called (not when defined), so ``KIRO_AGENTS_DIR`` can be redirected.
    Profiles of other orgs, and the legacy global ``orgmcp[-tools].json`` files, are never touched.
    """
    agents_dir = Path(agents_dir) if agents_dir is not None else Path(_patched("KIRO_AGENTS_DIR"))
    provisioner = wire_kiro.provisioner_at(
        org.root, agents_dir, wire_kiro.FunctionMcpServerLocator(_patched("mcp_server_command")),
        wire_kiro.FunctionConfinementPolicy(_patched("file_confinement")),
    )
    return cast(str, provisioner.ensure_profile(tools, workspace=workspace, inputs=inputs, confine=confine))


def kiro_runner(kiro_bin: str = "kiro-cli") -> Runner:
    def build(org: Org, addr: str, prompt: str) -> tuple[list[str], Path, dict[str, str]]:
        provisioner = wire_kiro.FunctionProfileProvisioner(
            lambda tools, **kw: _patched("ensure_kiro_profile")(tools, org=org, **kw),
            lambda tools: _patched("kiro_profile_name")(org.root, list(tools)),
        )
        command = wire_kiro.run_command_builder(org.runtime, kiro_bin, provisioner).build(addr, prompt)
        return list(command.argv), command.cwd, dict(command.env)

    return build


def _ps(pid: int) -> tuple[str, str] | None:
    """(state, start time) of a process as ``ps`` reports them; None when there is no such process.

    Raises OSError when ``ps`` itself cannot be run (the caller then has to treat the process as unknown).
    """
    try:
        info = wire_processes.system_inspector().info(pid)
    except ProcessTableError as exc:
        raise OSError(str(exc)) from exc
    return (info.state, info.started) if info else None


def _start_time(pid: int) -> str | None:
    return cast("str | None", wire_processes.system_inspector().start_time(pid))


def judge_orphan(rec: Mapping[str, object]) -> str:
    """Is the process recorded for a run of a dead scheduler still ours, and alive?

    * ``gone``: no such process (or a zombie): nothing to kill.
    * ``foreign``: the pid now belongs to something else (other start time, not a session leader): never touched.
    * ``ours``: alive, started at the recorded time, and the leader of its own session and process group, which is
      exactly how the scheduler starts runs. Only then may the group be killed.
    * ``doubt``: alive but unverifiable (no start time recorded, or ``ps`` failed): not killed, and the agent
      does not get a second run while it lives.
    """
    return cast(str, wire_processes.system_judge().judge(rec))


def kill_group(pgid: int, wait: float = 5.0) -> bool:
    """SIGKILL a process group and wait until its leader is gone. True when it is."""
    return cast(bool, wire_processes.system_signaller().kill_group(pgid, wait))


# ------------------------------------------------------- start/stop (used by the MCP tools of root)


def ignore_runtime_files(root: Path) -> None:
    """Keep files that change constantly out of the org's git snapshots (``git add -A`` after every run)."""
    _wire("wiring").open_runtime(Path(root)).ignore_list.ensure_runtime_files()


# EXIT_FILE, FINISHED and SchedulerState are the ones of ``orgmcp.daemon``; the functions below are thin adapters over the ``SchedulerStatus``,
# ``SchedulerControl`` and ``SchedulerCommand`` of the runtime in force (``wire_daemon``) until the scheduler itself (D-sched-1) and the callers of the
# status (C-obs-2, C-progress, C-dashdata) are converted. Each call uses the ports ``org.runtime`` has when it is made.


def scheduler_command(root: Path, max_runs: int | None = None, until_done: bool = False) -> list[str]:
    """``<this venv's orgmcp> --root <org> run [--max-runs N] [--until-done]`` (``python -m orgmcp`` if the script is missing)."""
    return cast("list[str]", wire_daemon.command_at(Path(root)).argv(max_runs, until_done))


def _command_line(pid: int) -> str | None:
    return cast("str | None", wire_processes.system_inspector().command_line(pid))


def _looks_like_scheduler_of(command: str, root: Path) -> bool:
    """Does this command line plausibly start the scheduler of the organization at ``root``? (see ``SchedulerIdentity``)"""
    return cast(bool, wire_daemon.identity().recognises(command, root))


def scheduler_state(org: Org) -> SchedulerState:
    """Is a scheduler running for ``org``? Read from ``.runtime/scheduler.pid`` and checked against the process table."""
    return cast(SchedulerState, wire_daemon.status_of(org.runtime).state())


def describe_scheduler(org: Org) -> str:
    return cast(str, wire_daemon.status_of(org.runtime).describe())


def waiting_on_user(
    org: Org, *, running: Collection[str] | None = None, blocked: Collection[str] = (), can_start: bool = True
) -> Waiting | None:
    """Is every open root task unable to progress without the user? None if not (or root has no open task).

    True when nothing runs and no agent could start a run (``running``/``blocked``: the scheduler's own view, default
    the inflight mailboxes; ``can_start=False``: the run cap is spent), yet root still waits for a result. The holders
    are then paused for budget or repeated failures, or stalled with nothing happening, or gone. Read-only.
    """
    return cast("Waiting | None", wire_attention.waiting_on_user_of(org.runtime).analyze(running=running, blocked=blocked, can_start=can_start))


def start_scheduler(org: Org, max_runs: int | None = None, until_done: bool = False) -> int:
    """Launch a detached scheduler for ``org`` (own session; output to ``.runtime/scheduler.log``). Returns its pid.

    ``until_done``: the scheduler exits by itself when root has no open task and nothing is running or runnable."""
    return cast(int, wire_daemon.control_of(org.runtime).start(max_runs, until_done))


def stop_scheduler(org: Org, wait: float = 15.0) -> str:
    """SIGTERM the org's scheduler (pid from the pidfile), only after checking that it is really that scheduler.

    The scheduler shuts down cleanly: runs in flight are interrupted (their batch is redelivered later).
    """
    return cast(str, wire_daemon.control_of(org.runtime).stop(wait))


class _RunnerCommands(RunCommandBuilder):
    """A legacy runner ``(org, addr, prompt) -> (argv, cwd, env)`` - whatever ``Scheduler.runner`` is when the run starts - as the command builder of the lifecycle."""

    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler

    def build(self, addr: str, prompt: str) -> RunCommand:
        argv, cwd, env = self._scheduler.runner(self._scheduler.org, addr, prompt)
        return RunCommand(tuple(argv), cwd, env)


class _EchoConsole(Console):
    """The output of the scheduler: whatever ``Scheduler.echo`` is when a line is said."""

    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler

    def say(self, line: str) -> None:
        self._scheduler.echo(line)


class FunctionClock(Clock):
    """A ``Clock`` whose time is a function (``Scheduler(clock=...)``): ``now`` and ``time`` follow it, waits are the system's. It is the cadence clock of the
    legacy scheduler (the stall ladder, the review, the heartbeat, the grace period and the guard); a run is timed by the system's."""

    def __init__(self, seconds: Callable[[], float]) -> None:
        self._seconds = seconds

    def now(self) -> datetime:
        return datetime.fromtimestamp(self._seconds(), timezone.utc)

    def time(self) -> float:
        return self._seconds()

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class _Loops:
    """The loop of a legacy scheduler over the ports of ``org.runtime`` as they are now: tests replace the runtime under a running scheduler, so the loop
    is made again, over the new runtime, with the state (the runs, the count, how it runs) and the memory of the old."""

    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler
        self._seen: object = None
        self._built: HeartbeatLoop | None = None

    def current(self) -> HeartbeatLoop:
        s = self._scheduler
        runtime = s.org.runtime
        if self._built is None or runtime is not self._seen:
            self._built = _wire("wire_scheduler").loop_of(
                runtime, _RunnerCommands(s), _EchoConsole(s), FunctionClock(lambda: s.clock()), s._state, s._memory, s._ports
            )
            self._seen = runtime
        return self._built


class Scheduler(SchedulerLoop):
    """The legacy surface of the scheduler: an ``Org``, a runner, an output and a clock, over the ``HeartbeatLoop`` that ``org.runtime`` makes. ``clock`` is
    the cadence clock only (stall detection, review, heartbeat and grace period, so tests can move time without sleeping); runs are timed by the system's.
    ``ports`` put other objects in the place of ports of the runtime for this scheduler (a test's failing stall ladder)."""

    def __init__(
        self,
        org: Org,
        runner: Runner | None = None,
        echo: Callable[[str], None] = print,
        clock: Callable[[], float] = time.time,
        *,
        ports: Mapping[type, object] | None = None,
    ):
        self.org = org
        self.runner = runner or kiro_runner()
        self.echo = echo
        self.clock = clock
        self._state = LoopState()
        self._memory = LoopMemory()
        self._ports: Mapping[type, object] = dict(ports or {})
        self._loops = _Loops(self)

    # --------------------------------------------------------- what the loop owns

    @property
    def runs(self) -> RunTable:
        return self._state.runs

    @runs.setter
    def runs(self, value: RunTable) -> None:
        self._state.runs = value

    @property
    def _count(self) -> RunCount:
        return self._state.count

    @property
    def _blocked(self) -> set[str]:
        return self._state.blocked

    @property
    def total_runs(self) -> int:
        return self._state.count.total

    @total_runs.setter
    def total_runs(self, value: int) -> None:
        self._state.count.total = value

    @property
    def mode(self) -> str:
        return self._state.mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._state.mode = value

    @property
    def max_runs(self) -> int | None:
        return self._state.max_runs

    @max_runs.setter
    def max_runs(self, value: int | None) -> None:
        self._state.max_runs = value

    @property
    def exit_reason(self) -> str:
        return self._state.exit_reason

    @exit_reason.setter
    def exit_reason(self, value: str) -> None:
        self._state.exit_reason = value

    # ------------------------------------------------------------ the loop

    def acquire(self) -> None:
        self._loops.current().acquire()

    def release(self) -> None:
        self._loops.current().release()

    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        self._loops.current().serve(until_idle, max_runs, until_done)

    def run_once(self, max_runs: int | None = None) -> None:
        self._loops.current().run_once(max_runs)

    def tick(self, max_runs: int | None = None) -> bool:
        """One pass: reap finished runs, start new ones, detect stalls, review health. Returns True if work remains."""
        return self._loops.current().tick(max_runs)

    def finished(self, max_runs: int | None = None) -> bool:
        """Is there nothing left for this scheduler: root has no open task, no run is in flight, no agent could start?"""
        return self._loops.current().finished(max_runs)

    def waiting_on_user(self, max_runs: int | None = None) -> Waiting | None:
        """``waiting_on_user`` with this scheduler's own view of what runs (read-only)."""
        return self._loops.current().waiting_on_user(max_runs)

    def _runnable(self) -> list[str]:
        return cast("list[str]", self.org.runtime.runnable_query.runnable(exclude=set(self.runs) | self._blocked))

    def _start(self, addr: str) -> None:
        self._loops.current().start(addr)

    def _reap(self) -> None:
        self._loops.current().reap()


def nothing_to_do(org: Org) -> bool:
    """Would an until-done scheduler exit at once? (root has no open task and no agent has work it could start)"""
    return cast(bool, wire_attention.open_work_of(org.runtime).nothing_to_do())
