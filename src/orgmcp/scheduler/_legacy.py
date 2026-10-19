"""The heartbeat: wake an agent for one fresh, short run whenever its inbox has messages.

One agent runs at most once at a time; different agents run in parallel. A run is a separate
process (kiro-cli by default) whose orgmcp MCP server is bound to the agent via ORG_AGENT.
"""

from __future__ import annotations

import importlib
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Collection, Mapping
from typing import Any, Callable, cast

from .. import review, telemetry
from ..attention import Waiting
from ..daemon import FINISHED, SchedulerState
from ..kernel import ROOT
from ..kiro import RunCommand, RunCommandBuilder
from ..processes import ProcessTableError
from ..settings import config_number
from ..runs import run_id_of
from ._assembly import Lifecycle
from ._ports import Console, PhaseGuard
from ._run import RunCount, RunRecord, RunTable

Run = RunRecord  # the old name of the data of a run in flight
Org = Any  # the facade: an entry point may not import it, so the legacy class takes whatever has a ``runtime`` (as the callers pass it)


def _wire(name: str) -> Any:
    """The composition root's module ``orgmcp.app.<name>``, looked up late: an entry point may not import ``orgmcp.app`` (the layers contract), and
    these legacy functions have no runtime to take their ports from. They go with the legacy surface (E3)."""
    return importlib.import_module(f"orgmcp.app.{name}")


wire_attention, wire_daemon, wire_kiro, wire_processes, wire_stalls = (
    _wire("wire_attention"), _wire("wire_daemon"), _wire("wire_kiro"), _wire("wire_processes"), _wire("wire_stalls"))

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


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("orgmcp")
    except Exception:  # noqa: BLE001
        return "unknown"


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


class _SchedulerGuard(PhaseGuard):
    """The best-effort guard of the scheduler's own ``_guard`` (the loop keeps it until D-sched-2)."""

    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler

    def guard(self, phase: str, fn: Callable[[], None]) -> None:
        self._scheduler._guard(phase, fn)


class _Lifecycles:
    """The starter and the reaper of a legacy scheduler over the ports of ``org.runtime`` as they are now: tests replace the runtime under a running scheduler."""

    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler
        self._seen: object = None
        self._built: Lifecycle | None = None

    def current(self) -> Lifecycle:
        s = self._scheduler
        runtime = s.org.runtime
        if self._built is None or runtime is not self._seen:
            self._built = _wire("wire_scheduler").lifecycle_of(runtime, _RunnerCommands(s), _EchoConsole(s), _SchedulerGuard(s), s._count)
            self._seen = runtime
        return self._built


class Scheduler:
    def __init__(
        self,
        org: Org,
        runner: Runner | None = None,
        echo: Callable[[str], None] = print,
        clock: Callable[[], float] = time.time,
    ):
        self.org = org
        self.runner = runner or kiro_runner()
        self.echo = echo
        self.clock = clock  # stall detection and review cadence, so tests can move time without sleeping
        self.runs: RunTable = {}
        self._count = RunCount()  # the runs started: the preparation of a run counts it, the cap ``max_runs`` reads it
        self._lifecycles = _Lifecycles(self)
        self._phase_errors: dict[str, str] = {}
        self._stalls = wire_stalls.RuntimeStalls(lambda: self.org.runtime, lambda: self.clock())  # the stall ladder, over the runtime in force
        self._blocked: set[str] = set()  # agents whose orphaned run (of a dead scheduler) is alive and could not be killed
        self._waiting_since: float | None = None  # until-done: since when nothing can progress without the user
        self.mode = "daemon"  # daemon | until_done | until_idle | once (for the scheduler.start event)
        self.max_runs: int | None = None
        self.exit_reason = "stopped"
        self._heartbeat_at: float | None = None
        self._pruned_at: float | None = None
        self._error_emitted: dict[str, tuple[str, float]] = {}

    @property
    def total_runs(self) -> int:
        return self._count.total

    @total_runs.setter
    def total_runs(self, value: int) -> None:
        self._count.total = value

    # ------------------------------------------------------------- lifecycle

    def _emit(self, kind: str, **fields: Any) -> None:
        """An event of the scheduler itself (never raises)."""
        telemetry.emit(self.org.root, kind, proc="scheduler", actor="runtime", **fields)

    def acquire(self) -> None:
        telemetry.set_process("scheduler")
        self.org.runtime.scheduler_lock.acquire()  # refuses while another live scheduler holds the pidfile
        self.org.runtime.exit_marker.clear()
        self._ignore_running_ledger()
        self._emit("scheduler.start", mode=self.mode, max_runs=self.max_runs,
                   max_parallel=config_number(self.org.config, "max_parallel", int), version=_version())
        self._settle_orphans()  # before recover(): never redeliver a batch while its previous run still lives
        for a in self.org.recover():
            self.echo(f"recovered interrupted run of {a}")

    # --------------------------------------------------- runs of a dead scheduler

    def _ignore_running_ledger(self) -> None:
        """The record changes with every run; keep it out of the org's git snapshots."""
        self.org.runtime.ignore_list.ensure_runtime_files()

    def _settle_orphans(self) -> None:
        """Kill runs a dead scheduler left behind, and note those that survive.

        Called when a scheduler starts (any record then belongs to a dead one: ``acquire`` has just checked that
        no other scheduler lives) and every tick while some orphan could not be dealt with. A recorded process is
        killed only if ``judge_orphan`` says it is ours; one that is alive but cannot be verified or killed keeps
        its agent from starting a new run until it is gone.
        """
        records = self.org.runtime.run_registry.all()
        keep = {}
        for addr, rec in records.items():
            if addr in self.runs or (self._blocked and addr not in self._blocked):
                keep[addr] = rec
                continue
            verdict = judge_orphan(rec)
            pgid = rec.get("pgid")
            rid = run_id_of(addr, rec["log"]) if rec.get("log") else None
            if verdict == "ours":
                if kill_group(pgid):
                    self.echo(f"{addr}: killed the orphaned run of a dead scheduler (process group {pgid})")
                    self._note_in_log(rec, "killed: orphaned run of a scheduler that died")
                    self._emit("run.orphan", agent=addr, run=rid, action="killed",
                               detail=f"process group {pgid} of a dead scheduler killed; its batch is redelivered")
                    verdict = "gone"
                else:
                    verdict = "doubt"
            elif verdict == "gone":
                self._emit("run.orphan", agent=addr, run=rid, action="redelivered",
                           detail="the process of a dead scheduler's run is gone; its batch is redelivered")
            if verdict == "foreign":
                self.echo(f"{addr}: recorded process {pgid} is not the run we started; left alone")
                self._emit("run.orphan", agent=addr, run=rid, action="redelivered",
                           detail=f"pid {pgid} now belongs to another process (left alone); the run's batch is redelivered")
            elif verdict == "doubt":
                if addr not in self._blocked:
                    self._emit("run.orphan", agent=addr, run=rid, action="kept",
                               detail=f"process group {pgid} may be alive and cannot be verified or killed; no new run until it is gone")
                keep[addr] = rec
                if addr not in self._blocked:
                    self.echo(f"{addr}: an earlier run (process group {pgid}) may still be alive and cannot be "
                              "verified or killed; no new run until it is gone")
                self._blocked.add(addr)
                continue
            self._blocked.discard(addr)
        self._blocked &= set(keep)
        if keep != records:
            self.org.runtime.run_registry.replace(keep)

    def _note_in_log(self, rec: dict[str, object], text: str) -> None:
        try:
            rel = str(rec["log"])
        except KeyError:
            return
        self.org.runtime.run_log_writer.append_note(rel, text)

    def release(self) -> None:
        self._lifecycles.current().reaper.terminate_all(self.runs)
        self.org.runtime.scheduler_lock.release()
        self._emit("scheduler.exit", reason=telemetry.clip(self.exit_reason, telemetry.ERROR_MAX),
                   runs_started=self.total_runs)

    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        self.mode = "until_done" if until_done else "until_idle" if until_idle else "daemon"
        self.max_runs = max_runs
        self.acquire()
        stop = False

        def on_signal(*_: object) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGTERM, on_signal)
        try:
            while not stop:
                active = self.tick(max_runs=max_runs)
                if until_idle and not active:
                    self.echo("organization is idle")
                    self.exit_reason = "idle: nothing left to do"
                    break
                if until_done and self.finished(max_runs):
                    self.echo(f"scheduler exiting: {FINISHED}")
                    self.org.runtime.exit_marker.write(FINISHED)
                    self.exit_reason = FINISHED
                    break
                if until_done and (reason := self._check_waiting(max_runs)):
                    self.echo(f"scheduler exiting: {reason}")
                    self.org.runtime.exit_marker.write(reason)
                    self.exit_reason = reason
                    break
                time.sleep(config_number(self.org.config, "poll_seconds"))
            else:
                self.exit_reason = "stopped by SIGTERM"
        except KeyboardInterrupt:
            self.exit_reason = "interrupted (KeyboardInterrupt)"
        except Exception as exc:
            self.exit_reason = f"error: {type(exc).__name__}: {exc}"
            raise
        finally:
            self.release()

    # ------------------------------------------------------------------ tick

    def tick(self, max_runs: int | None = None) -> bool:
        """One pass: reap finished runs, start new ones, detect stalls, review health. Returns True if work remains."""
        self._repair_failures_ledger()
        self._reap()
        if self._blocked:
            self._guard("orphan check", self._settle_orphans)
        self._resume_funded()
        if max_runs is None or self.total_runs < max_runs:
            self._launch(max_runs)
        self._guard("stall check", self._check_stalls)  # best-effort phases: a bug or bad data here
        self._guard("health review", self._check_review)  # must never stop agents from running
        self._guard("event log upkeep", lambda: self._upkeep_events(max_runs))
        return bool(self.runs) or (bool(self._runnable()) and (max_runs is None or self.total_runs < max_runs))

    def _upkeep_events(self, max_runs: int | None) -> None:
        """The heartbeat event (every ``heartbeat_seconds``) and the daily pruning of old event-log days."""
        now = self.clock()
        cfg = self.org.config
        if self._heartbeat_at is None or now - self._heartbeat_at >= config_number(cfg, "heartbeat_seconds"):
            self._heartbeat_at = now
            _human_items = importlib.import_module("orgmcp.progress")._human_items  # late: the legacy module is above the entry points

            self._emit("scheduler.heartbeat", running=sorted(r.run_id for r in self.runs.values()),
                       runnable=len(self._runnable()), waiting_on_you=len(_human_items(self.org)))
        if self._pruned_at is None or now - self._pruned_at >= 86400:
            self._pruned_at = now
            removed = telemetry.prune(self.org.root, int(config_number(cfg, "events_keep_days", int)))
            if removed:
                self._emit("prune", removed_days=removed)

    def waiting_on_user(self, max_runs: int | None = None) -> Waiting | None:
        """``waiting_on_user`` with this scheduler's own view of what runs (read-only)."""
        return waiting_on_user(self.org, running=set(self.runs), blocked=self._blocked,
                               can_start=max_runs is None or self.total_runs < max_runs)

    def _check_waiting(self, max_runs: int | None = None) -> str:
        """Until-done: the exit reason once nothing has been able to progress without the user for the grace period
        (``until_done_grace_seconds``), else ''. Anything that changes the picture (a grant, a resume, a new task)
        starts the count again. A task that is merely stalled also waits for the stall ladder to reach root."""
        waiting = self.waiting_on_user(max_runs)
        if waiting is None:
            self._waiting_since = None
            return ""
        now = self.clock()
        if self._waiting_since is None:
            self._waiting_since = now
            self.echo(f"{waiting.text}. Exiting in {config_number(self.org.config, 'until_done_grace_seconds'):.0f}s "
                      "unless something changes")
        if not waiting.settled or now - self._waiting_since < config_number(self.org.config, "until_done_grace_seconds"):
            return ""
        return waiting.text

    def finished(self, max_runs: int | None = None) -> bool:
        """Is there nothing left for this scheduler: root has no open task, no run is in flight, no agent could start?"""
        can_start = max_runs is None or self.total_runs < max_runs
        return not self.org.outstanding(ROOT) and not self.runs and not (can_start and self._runnable())

    def _repair_failures_ledger(self) -> None:
        """The failure counts drive pausing; a wrong-shaped ledger would raise inside ``record_failure``."""
        if self.org.runtime.failure_counter.repair():
            self.echo("repaired malformed .runtime/failures.json")

    def _guard(self, phase: str, fn: Callable[[], None]) -> None:
        """Run a best-effort phase; log (once per distinct error) instead of raising out of the loop."""
        try:
            fn()
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            if self._phase_errors.get(phase) != message:
                self._phase_errors[phase] = message
                self.echo(f"{phase} failed (will retry next tick): {message}")
            last = self._error_emitted.get(phase)  # a fault that persists is recorded when it changes, then every minute
            if last is None or last[0] != message or self.clock() - last[1] >= 60:
                self._error_emitted[phase] = (message, self.clock())
                self._emit("scheduler.error", phase=phase, error=telemetry.clip(message, telemetry.ERROR_MAX))
        else:
            self._phase_errors.pop(phase, None)

    def _resume_funded(self) -> None:
        """Lift a budget pause once budget is back (a refund note arrives without waking anyone)."""
        for addr in self.org.agents():
            if self.org.paused(addr) == "budget" and (self.org.budget(addr) or 0) > 0:
                self.org.resume(addr, "budget is back", by="runtime")
                self.echo(f"{addr}: budget is back, resumed")

    def _runnable(self) -> list[str]:
        return cast("list[str]", self.org.runtime.runnable_query.runnable(exclude=set(self.runs) | self._blocked))

    def _launch(self, max_runs: int | None) -> None:
        self._lifecycles.current().starter.launch(self.runs, self._blocked, max_runs)

    def _start(self, addr: str) -> None:
        self._lifecycles.current().starter.start(self.runs, addr)

    def _reap(self) -> None:
        self._lifecycles.current().reaper.reap(self.runs)

    # --------------------------------------------------------------- reviews

    def _check_review(self) -> None:
        """Start a health review when one is due (see ``review.review_if_due``)."""
        done = review.review_if_due(self.org, datetime.fromtimestamp(self.clock(), timezone.utc))
        if done and done.notes:
            self.echo(f"health review: {done.flagged} flagged, told {', '.join(n.to for n in done.notes)}")

    # ---------------------------------------------------------------- stalls

    def _check_stalls(self) -> None:
        """Climb the escalation ladder for every open task whose assignee has gone quiet (``stalls.StallLadder``)."""
        for line in self._stalls.check():
            self.echo(line)

    def _task_view(self, addr: str, view: str) -> list[Any]:
        """``open_tasks`` / ``outstanding`` of an agent as the stall ladder sees them (kept until the tests that read it move: D-sched-1)."""
        return cast("list[Any]", self._stalls.task_view(addr, view))

    def _last_run_end(self, addr: str) -> float:
        return cast(float, self.org.runtime.run_log_reader.last_end(addr))


def nothing_to_do(org: Org) -> bool:
    """Would an until-done scheduler exit at once? (root has no open task and no agent has work it could start)"""
    return cast(bool, wire_attention.open_work_of(org.runtime).nothing_to_do())
