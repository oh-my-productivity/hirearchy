"""The heartbeat: wake an agent for one fresh, short run whenever its inbox has messages.

One agent runs at most once at a time; different agents run in parallel. A run is a separate
process (kiro-cli by default) whose orgmcp MCP server is bound to the agent via ORG_AGENT.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple

from . import review, telemetry, templates
from .app import wire_processes
from .app.wiring import open_runtime
from .core import ROOT, Org, OrgError, atomic_write
from .health import config_number
from .processes import ProcessTableError
from .runs import (
    RunLogSink,
    log_exit,
    log_failed_start,
    log_header,
    log_interrupted,
    log_invocation,
    log_note,
    log_prompt,
    log_retired,
    log_timeout,
    run_id_of,
    run_record,
)

# (org, agent address, prompt) -> (argv, cwd, env). The prompt is delivered on the process's stdin, not in argv.
Runner = Callable[[Org, str, str], tuple[list[str], Path, dict]]

PROJECT_DIR = Path(__file__).resolve().parents[2]
KIRO_AGENTS_DIR = Path.home() / ".kiro" / "agents"


def mcp_server_command() -> dict:
    """How kiro should start the orgmcp MCP server (prefer the venv's console script)."""
    script = Path(sys.executable).with_name("orgmcp")
    if script.exists():
        return {"command": str(script), "args": ["mcp"]}
    return {"command": shutil.which("uv") or "uv", "args": ["--directory", str(PROJECT_DIR), "run", "orgmcp", "mcp"]}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def kiro_profile_name(org_root: str | Path, tools: list[str]) -> str:
    """``orgmcp-<org-slug>-<6-char hash of the org root path>[-<tools>]``, lowercase ``[a-z0-9-]``.

    The hash makes the name unique per organization (two ``.../org`` dirs never share a profile); the slug only
    makes it recognizable. Profiles of different orgs therefore never overwrite each other.
    """
    root = Path(org_root).expanduser().resolve()
    base = root.name
    if base.lower() == "org" and root.parent.name:  # "org" alone says nothing: use "<parent>-org"
        base = f"{root.parent.name}-org"
    slug = _slug(base)[:24].strip("-") or "org"
    digest = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:6]
    return "-".join(["orgmcp", slug, digest, *(_slug(t) for t in sorted(set(tools)) if _slug(t))])


FILE_TOOLS = ("read", "write")  # kiro built-ins whose reach can be limited by path (shell cannot)


def file_confinement(
    org_root: Path, tools: list[str], workspace: Path | None, inputs: list[Path]
) -> tuple[list[str], dict]:
    """(allowedTools, toolsSettings) that confine kiro's built-in ``read``/``write`` by path.

    Verified against kiro-cli 2.29.1 (see README, "Workspaces, inputs and confinement"):
    * ``read``/``write`` must NOT be in ``allowedTools``: a tool there ignores ``allowedPaths``. Left out, a call inside
      ``allowedPaths`` runs unprompted and any other path asks for an approval, which ``--no-interactive`` cannot
      give, so it is refused.
    * ``write``: only under the workspace (``[]`` without one: nowhere). ``read``: workspace + inputs + the organization
      (read-only: orgmcp's own ``read`` may read anything in the org, and an agent that holds the built-in ``read``
      sees only that one: it hides orgmcp's ``read``, same short name, see studies/F-read-experiment); a directory
      needs both ``P`` and ``P/**`` to be listable.
    * ``deniedPaths`` on the org directory is a hard deny even for kiro's own "current directory is readable" rule:
      the org is never written with kiro's tools (orgmcp ``write`` does that), so ``write`` keeps the deny. ``read``
      has none: a deny would beat the allow above. Skipped when the workspace is inside the org.
    * ``shell`` stays in ``allowedTools`` and is NOT confined (kiro has no path rule for it).
    """
    org_root = Path(org_root).resolve()
    deny = [] if workspace is not None and (workspace == org_root or org_root in workspace.parents) else [str(org_root), f"{org_root}/**"]
    settings: dict = {}
    if "write" in tools:
        settings["write"] = {"allowedPaths": [f"{workspace}/**"] if workspace is not None else [], "deniedPaths": deny}
    if "read" in tools:
        bases = [p for p in (workspace, *inputs, org_root) if p is not None]
        settings["read"] = {"allowedPaths": list(dict.fromkeys(x for p in bases for x in (str(p), f"{p}/**"))), "deniedPaths": []}
    return [t for t in tools if t not in FILE_TOOLS], settings


def ensure_kiro_profile(
    tools: list[str], agents_dir: Path | None = None, *, org: Org,
    workspace: Path | None = None, inputs: list[Path] | None = None, confine: bool = False,
) -> str:
    """Write the scheduler's profile for ``org`` into ``~/.kiro/agents``: only the orgmcp server plus the granted tools.

    The profile is internal to this organization: its MCP server entry carries ``ORG_ROOT`` (this org) and
    ``ORG_REQUIRE_AGENT=1``, so used outside the scheduler (no ``ORG_AGENT``) the server refuses to start instead of
    acting as ``root``. ``ORG_AGENT`` itself is NOT baked in: it comes from the scheduler's process environment
    (assumption: kiro starts MCP servers with its own environment plus the profile's ``env``; if it did not, the
    server would fail closed and the run would fail visibly rather than act as root).

    ``confine=False``: the shared profile of the org for this tool set; every granted tool runs unprompted.
    ``confine=True``: the profile of an agent with built-in ``read``/``write``: they are limited to ``workspace`` (write)
    and ``workspace`` + ``inputs`` + the org itself (read), see :func:`file_confinement`. Its name carries a hash of that access, so
    agents with the same tools and access share a profile and different access never does.

    The directory is resolved when called (not when defined), so ``KIRO_AGENTS_DIR`` can be redirected.
    Profiles of other orgs, and the legacy global ``orgmcp[-tools].json`` files, are never touched.
    """
    agents_dir = Path(agents_dir) if agents_dir is not None else Path(KIRO_AGENTS_DIR)
    tools = sorted(set(tools))
    name = kiro_profile_name(org.root, tools)
    allowed, settings = ["@orgmcp", *tools], {}
    if confine:
        allowed, settings = file_confinement(org.root, tools, workspace, list(inputs or []))
        allowed = ["@orgmcp", *allowed]
        name += "-x" + hashlib.sha1(json.dumps(settings, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    server = {**mcp_server_command(), "env": {"ORG_ROOT": str(org.root), "ORG_REQUIRE_AGENT": "1"}}
    data = templates.kiro_profile(
        name,
        f"internal: used by the orgmcp scheduler for {org.root}; not a general-purpose agent"
        + (f" (built-in tools: {', '.join(tools)})" if tools else ""),
        ["@orgmcp", *tools],
        server,
        allowed_tools=allowed,
        tools_settings=settings,
    )
    path = agents_dir / f"{name}.json"
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # missing or corrupt: rewrite it
        current = None
    if current != data:
        atomic_write(path, json.dumps(data, indent=2) + "\n")  # temp file + rename: never a half-written profile
    return name


def kiro_runner(kiro_bin: str = "kiro-cli") -> Runner:
    def build(org: Org, addr: str, prompt: str) -> tuple[list[str], Path, dict]:
        meta, _ = org.charter(addr)
        tools = list(meta.get("tools") or [])
        # An agent with built-in read/write gets a profile that confines them by path. The one exception is a legacy
        # charter (built-in `read` only, no workspace, no `inputs` key), which keeps the unconfined profile it always had.
        legacy = "write" not in tools and org.unconfined_read(meta)
        if set(tools) & set(FILE_TOOLS) and not legacy:
            profile = ensure_kiro_profile(
                tools, org=org, workspace=org.workspace_of(addr), inputs=org.inputs_of(addr), confine=True
            )
        else:
            profile = ensure_kiro_profile(tools, org=org)
        cmd = [kiro_bin, "chat", "--no-interactive", "--agent", profile]
        cmd += ["--model", org.model_for(addr)]  # always explicit: charter model > org default_model > DEFAULT_MODEL
        # The prompt is not an argument: it can be arbitrarily long (E2BIG) and visible in `ps`.
        # `kiro-cli chat --no-interactive` without INPUT reads it from stdin; the scheduler feeds it there.
        ws = meta.get("workspace")
        cwd = Path(ws).expanduser() if ws else org.dir(addr)
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr}
        return cmd, cwd, env

    return build


@dataclass
class Run:
    addr: str
    proc: subprocess.Popen
    log: Path
    logf: RunLogSink
    started: float
    batch: int
    strays: dict | None = None  # paths of the agent's workspace that could hold stray org files, before the run
    run_id: str = ""  # "<agent>@<run log stem>": the id events and the agent's MCP server (ORG_RUN_ID) carry
    traces: tuple = ()  # distinct traces of the batch
    budget_before: int | None = None
    killed: bool = False
    timed_out: bool = False


def _signal_group(proc: subprocess.Popen, sig: int) -> None:
    """Signal a run's whole process group (the run was started in its own session, so pgid == pid)."""
    wire_processes.adopt(proc).signal_group(sig)


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
    return wire_processes.system_inspector().start_time(pid)


def judge_orphan(rec: dict) -> str:
    """Is the process recorded for a run of a dead scheduler still ours, and alive?

    * ``gone``: no such process (or a zombie): nothing to kill.
    * ``foreign``: the pid now belongs to something else (other start time, not a session leader): never touched.
    * ``ours``: alive, started at the recorded time, and the leader of its own session and process group, which is
      exactly how the scheduler starts runs. Only then may the group be killed.
    * ``doubt``: alive but unverifiable (no start time recorded, or ``ps`` failed): not killed, and the agent
      does not get a second run while it lives.
    """
    return wire_processes.system_judge().judge(rec)


def kill_group(pgid: int, wait: float = 5.0) -> bool:
    """SIGKILL a process group and wait until its leader is gone. True when it is."""
    return wire_processes.system_signaller().kill_group(pgid, wait)


# ------------------------------------------------------- start/stop (used by the MCP tools of root)


def ignore_runtime_files(root: Path) -> None:
    """Keep files that change constantly out of the org's git snapshots (``git add -A`` after every run)."""
    open_runtime(Path(root)).ignore_list.ensure_runtime_files()


EXIT_FILE = ".runtime/scheduler.exit"  # why the last scheduler exited by itself (until-done); removed when one starts
FINISHED = "finished: no open tasks"


class SchedulerState(NamedTuple):
    """``state``: stopped | running (verified to be this org's scheduler) | unverified (pid alive, not trusted)."""
    state: str
    pid: int | None = None
    since: str | None = None
    detail: str = ""


def scheduler_command(root: Path, max_runs: int | None = None, until_done: bool = False) -> list[str]:
    """``<this venv's orgmcp> --root <org> run [--max-runs N] [--until-done]`` (``python -m orgmcp`` if the script is missing)."""
    script = Path(sys.executable).with_name("orgmcp")
    base = [str(script)] if script.exists() else [sys.executable, "-m", "orgmcp"]
    return [*base, "--root", str(root), "run", *(["--max-runs", str(max_runs)] if max_runs is not None else []),
            *(["--until-done"] if until_done else [])]


def _command_line(pid: int) -> str | None:
    return wire_processes.system_inspector().command_line(pid)


def _root_arguments(tokens: list[str]) -> list[str]:
    """The values given to ``--root`` in a command line."""
    return [tokens[i + 1] for i, t in enumerate(tokens[:-1]) if t == "--root"] + [t[7:] for t in tokens if t.startswith("--root=")]


def _same_dir(path: str, root: Path) -> bool:
    """Is ``path`` the directory ``root`` under another spelling (a symlink such as macOS /tmp -> /private/tmp, ``~``)?"""
    if not path.startswith(("/", "~")):
        return False  # relative to the other process's working directory: cannot be compared
    try:
        return Path(path).expanduser().resolve() == root.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def _looks_like_scheduler_of(command: str, root: Path) -> bool:
    """Does this command line plausibly start the scheduler of the organization at ``root``?

    Needs the ``run`` subcommand and either the org's root path or an ``orgmcp`` program. A ``--root`` that is not
    this org (or cannot be compared, being relative) is a no.
    """
    tokens = command.split()
    names_root = str(root) in command or any(_same_dir(t, root) for t in _root_arguments(tokens))
    has_root_flag = any(t == "--root" or t.startswith("--root=") for t in tokens)
    has_orgmcp = any(Path(t).name == "orgmcp" for t in tokens)
    return "run" in tokens and (names_root or (has_orgmcp and not has_root_flag))


_children: dict[int, subprocess.Popen] = {}  # schedulers this process started: reaped so they never linger as zombies


def _reap_children() -> None:
    for pid, proc in list(_children.items()):
        if proc.poll() is not None:
            del _children[pid]


def scheduler_state(org: Org) -> SchedulerState:
    """Is a scheduler running for ``org``? Read from ``.runtime/scheduler.pid`` and checked against the process table."""
    _reap_children()
    pidfile = org.root / ".runtime" / "scheduler.pid"
    try:
        pid = int(pidfile.read_text().strip())
        since = datetime.fromtimestamp(pidfile.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    except (OSError, ValueError):
        return SchedulerState("stopped")
    if pid <= 1:
        return SchedulerState("stopped")
    try:
        info = _ps(pid)
    except (OSError, subprocess.SubprocessError):
        return SchedulerState("unverified", pid, since, "the process table could not be read")
    if info is None or info[0].startswith("Z"):
        return SchedulerState("stopped")  # stale pidfile: the process is gone
    command = _command_line(pid)
    if command and _looks_like_scheduler_of(command, org.root):
        return SchedulerState("running", pid, since)
    return SchedulerState("unverified", pid, since, f"its command line is {command!r}" if command else "its command line is unknown")


def describe_scheduler(org: Org) -> str:
    st = scheduler_state(org)
    if st.state == "running":
        return f"scheduler: running (pid {st.pid}, since {st.since})"
    if st.state == "unverified":
        return (f"scheduler: unknown - .runtime/scheduler.pid names pid {st.pid}, which is alive but not verified "
                f"to be this org's scheduler ({st.detail}); not trusted")
    reason = _exit_reason(org)
    if not reason:
        waiting = waiting_on_user(org)
        reason = waiting.text if waiting else ""
    return f"scheduler: stopped ({reason})" if reason else "scheduler: stopped"


def _exit_reason(org: Org) -> str:
    """Why the scheduler last exited by itself, while that is still true (root has no open task); else ''."""
    try:
        reason = (org.root / EXIT_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return reason if reason and not org.outstanding(ROOT) else ""


class Waiting(NamedTuple):
    """Why open root tasks cannot move without the user. ``text``: "waiting on you: ..."; ``options``: what the user can
    do; ``settled``: False while the stall ladder (reminders to the holder) may still wake someone."""
    text: str
    options: str
    settled: bool = True


def _chain(org: Org, addr: str, task) -> list[str]:
    """Who hears about a stalled task, in order: the assignee, its assigner, then up the tree to root."""
    chain = [addr]
    up = task.sender if org.exists(task.sender) else org.parent(addr)
    while up:
        chain.append(up)
        up = org.parent(up)
    return chain


def _startable(org: Org, addr: str) -> bool:
    """Could a scheduler start a run of ``addr`` now? (unread mail, budget, and not paused for another reason)"""
    if not org.unread(addr) or (org.budget(addr) or 0) <= 0:
        return False
    return org.paused(addr) in (None, "budget")


def _names(addrs: list[str]) -> str:
    shown = ", ".join(addrs[:3])
    return shown + (f" and {len(addrs) - 3} more" if len(addrs) > 3 else "")


def waiting_on_user(org: Org, *, running=None, blocked=(), can_start: bool = True) -> Waiting | None:
    """Is every open root task unable to progress without the user? None if not (or root has no open task).

    True when nothing runs and no agent could start a run (``running``/``blocked``: the scheduler's own view, default
    the inflight mailboxes; ``can_start=False``: the run cap is spent), yet root still waits for a result. The holders
    are then paused for budget or repeated failures, or stalled with nothing happening, or gone. Read-only.
    """
    tasks = org.outstanding(ROOT)
    if not tasks:
        return None
    agents = org.agents()
    if (set(running) if running is not None else {a for a in agents if org.running(a)}) or blocked:
        return None
    if can_start and any(_startable(org, a) for a in agents):
        return None
    nudges = _nudge_entries(org.ledger("nudges"))
    texts: list[str] = []
    options: list[str] = []
    settled = True
    for t in tasks:
        title = f'"{t.title}"'
        team = [a for a in org.subtree(t.to) if a != ROOT] if org.exists(t.to) else []
        if not team:
            texts.append(f"{title} needs a decision ({t.to} no longer exists)")
            continue
        holding = [a for a in team if org.unread(a) or org.open_tasks(a)]
        failing = [a for a in holding if org.paused(a) not in (None, "budget")]
        short = [a for a in holding if a not in failing and (org.budget(a) or 0) <= 0]
        if failing:
            texts.append(f"{title} needs you to resume {_names(failing)} (it keeps failing)")
            options.append(f"a human runs `orgmcp resume {failing[0]}` and you call start()")
        elif short:
            texts.append(f"{title} needs budget ({_names(short)} out of runs)")
            options.append(f'grant runs with send(to="{t.to}", body="<why>", budget=N), then call start()')
        else:
            stalled = [a for a in team if org.open_tasks(a) and not org.outstanding(a)]
            who = f"{_names(stalled)} holds it and nothing is running" if stalled else "nothing is running"
            texts.append(f"{title} needs a decision ({who})")
            options.append(f'send(to="{t.to}", body=<instructions or a changed task>) and call start()')
            for a in stalled:  # the stall ladder (reminder, then escalation up to root) may still wake the holder
                for task in org.open_tasks(a):
                    last = nudges.get(task.id)
                    if (last["step"] if last else -1) < len(_chain(org, a, task)) - 1:
                        settled = False
    if not can_start:
        texts.append("the run cap (max_runs) was reached")
        options.append("start() again with a higher max_runs")
    choices = "; or ".join(dict.fromkeys(options + ["accept what exists so far (the task stays open: tell the user, and stop() the scheduler)"]))
    return Waiting("waiting on you: " + "; ".join(texts), "Your options: " + choices + ".", settled)


def start_scheduler(org: Org, max_runs: int | None = None, until_done: bool = False) -> int:
    """Launch a detached scheduler for ``org`` (own session; output to ``.runtime/scheduler.log``). Returns its pid.

    ``until_done``: the scheduler exits by itself when root has no open task and nothing is running or runnable."""
    if max_runs is not None and max_runs < 0:
        raise OrgError("max_runs must be 0 or more")
    st = scheduler_state(org)
    if st.state == "running":
        raise OrgError(f"a scheduler is already running for this org (pid {st.pid}, since {st.since}); call stop() first to restart it")
    if st.state == "unverified":
        raise OrgError(f"not starting: .runtime/scheduler.pid names pid {st.pid}, which is alive but not verified to be "
                       f"this org's scheduler ({st.detail}). Check that process; if it is stale, remove that file")
    runtime = org.root / ".runtime"
    runtime.mkdir(exist_ok=True)
    org.runtime.ignore_list.ensure_runtime_files()
    (org.root / EXIT_FILE).unlink(missing_ok=True)
    log = runtime / "scheduler.log"
    env = {**os.environ, "ORG_ROOT": str(org.root), "PYTHONUNBUFFERED": "1"}
    for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
        env.pop(var, None)
    cmd = scheduler_command(org.root, max_runs, True) if until_done else scheduler_command(org.root, max_runs)
    with open(log, "ab") as out:
        out.write(f"\n# --- scheduler started {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%SZ}: {' '.join(cmd)}\n".encode())
        out.flush()
        proc = subprocess.Popen(cmd, cwd=org.root, env=env, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, start_new_session=True)
    _children[proc.pid] = proc
    pidfile = runtime / "scheduler.pid"
    deadline = time.time() + 10
    while time.time() < deadline:
        code = proc.poll()
        if code == 0 and (org.root / EXIT_FILE).is_file():
            break  # it had nothing left to do and exited by itself (until-done): that is not a failure
        if code is not None:
            tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-5:])
            raise OrgError(f"the scheduler exited at once (exit {code}); {log} ends with:\n{tail}")
        try:
            if int(pidfile.read_text().strip()) == proc.pid:
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    return proc.pid


def stop_scheduler(org: Org, wait: float = 15.0) -> str:
    """SIGTERM the org's scheduler (pid from the pidfile), only after checking that it is really that scheduler.

    The scheduler shuts down cleanly: runs in flight are interrupted (their batch is redelivered later).
    """
    st = scheduler_state(org)
    if st.state == "stopped":
        return "no scheduler is running for this org"
    if st.state == "unverified":
        raise OrgError(f"not signalling pid {st.pid}: it is alive but not verified to be this org's scheduler "
                       f"({st.detail}). If it is, stop it yourself (kill {st.pid})")
    try:
        os.kill(st.pid, signal.SIGTERM)
    except ProcessLookupError:
        return f"scheduler (pid {st.pid}) was already gone"
    except PermissionError:
        raise OrgError(f"not allowed to signal pid {st.pid}")
    deadline = time.time() + wait
    while time.time() < deadline:
        _reap_children()
        try:
            info = _ps(st.pid)
        except (OSError, subprocess.SubprocessError):
            break
        if info is None or info[0].startswith("Z"):
            return f"scheduler stopped (pid {st.pid})"
        time.sleep(0.1)
    return (f"sent SIGTERM to the scheduler (pid {st.pid}); it is still shutting down (it interrupts agent runs first). "
            "Check status() shortly")


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("orgmcp")
    except Exception:  # noqa: BLE001
        return "unknown"


def _nudge_entries(raw) -> dict[str, dict]:
    """Entries of the nudges ledger in the current shape; malformed entries (or a malformed ledger) are dropped."""
    out: dict[str, dict] = {}
    for key, value in (raw.items() if isinstance(raw, dict) else ()):
        if isinstance(value, str):  # legacy ledger: "nudged" / "escalated"
            out[key] = {"step": 0 if value == "nudged" else 1, "at": 0}
        elif isinstance(value, dict):
            try:
                out[key] = {"step": max(0, int(value["step"])), "at": float(value.get("at") or 0)}
            except (KeyError, TypeError, ValueError):
                continue
    return out


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
        self.runs: dict[str, Run] = {}
        self.total_runs = 0
        self._phase_errors: dict[str, str] = {}
        self._task_memo: dict[str, tuple[tuple, dict]] = {}  # agent -> (mailbox fingerprint, cached task views)
        self.pidfile = org.root / ".runtime" / "scheduler.pid"
        self._blocked: set[str] = set()  # agents whose orphaned run (of a dead scheduler) is alive and could not be killed
        self._waiting_since: float | None = None  # until-done: since when nothing can progress without the user
        self.mode = "daemon"  # daemon | until_done | until_idle | once (for the scheduler.start event)
        self.max_runs: int | None = None
        self.exit_reason = "stopped"
        self._heartbeat_at: float | None = None
        self._pruned_at: float | None = None
        self._error_emitted: dict[str, tuple[str, float]] = {}

    # ------------------------------------------------------------- lifecycle

    def _emit(self, kind: str, **fields) -> None:
        """An event of the scheduler itself (never raises)."""
        telemetry.emit(self.org.root, kind, proc="scheduler", actor="runtime", **fields)

    def acquire(self) -> None:
        telemetry.set_process("scheduler")
        self.pidfile.parent.mkdir(parents=True, exist_ok=True)
        if self.pidfile.exists():
            try:
                pid = int(self.pidfile.read_text().strip())
                os.kill(pid, 0)
                alive = True
            except (ValueError, ProcessLookupError):
                alive = False
            except PermissionError:  # the pid exists but belongs to another user: it is alive
                alive = True
            if alive:
                raise OrgError(f"a scheduler is already running for this org (pid {pid})")
            self.pidfile.unlink()  # stale
        (self.org.root / EXIT_FILE).unlink(missing_ok=True)
        self.pidfile.write_text(str(os.getpid()))
        self._ignore_running_ledger()
        self._emit("scheduler.start", mode=self.mode, max_runs=self.max_runs,
                   max_parallel=config_number(self.org.config, "max_parallel", int), version=_version())
        self._settle_orphans()  # before recover(): never redeliver a batch while its previous run still lives
        for a in self.org.recover():
            self.echo(f"recovered interrupted run of {a}")

    # --------------------------------------------------- runs of a dead scheduler

    def _record_run(self, addr: str, run: Run) -> None:
        """``.runtime/running.json``: agent -> {pgid, lstart, started, scheduler, log} of every run in flight."""
        self.org.runtime.run_registry.record(addr, run_record(
            pgid=run.proc.pid,  # started in its own session, so pgid == pid
            lstart=_start_time(run.proc.pid),
            started=run.started,
            scheduler=os.getpid(),
            log=str(run.log.relative_to(self.org.root)),
        ))

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

    def _note_in_log(self, rec: dict, text: str) -> None:
        try:
            rel = str(rec["log"])
        except KeyError:
            return
        self.org.runtime.run_log_writer.append_note(rel, text)

    def release(self) -> None:
        for run in list(self.runs.values()):
            _signal_group(run.proc, signal.SIGTERM)
        for addr, run in list(self.runs.items()):
            try:
                run.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            _signal_group(run.proc, signal.SIGKILL)  # also reaps tool subprocesses that ignored SIGTERM
            run.proc.wait()
            run.logf.write(log_interrupted())
            run.logf.close()
            self.org.end_run(addr, ok=False)
            run.killed = True
            self._emit_run_end(run, run.proc.returncode, error="interrupted by scheduler shutdown")
        self.org.runtime.run_registry.forget(*self.runs)
        self.runs.clear()
        self.pidfile.unlink(missing_ok=True)
        self._emit("scheduler.exit", reason=telemetry.clip(self.exit_reason, telemetry.ERROR_MAX),
                   runs_started=self.total_runs)

    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        self.mode = "until_done" if until_done else "until_idle" if until_idle else "daemon"
        self.max_runs = max_runs
        self.acquire()
        stop = False

        def on_signal(*_):
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
                    atomic_write(self.org.root / EXIT_FILE, FINISHED + "\n")
                    self.exit_reason = FINISHED
                    break
                if until_done and (reason := self._check_waiting(max_runs)):
                    self.echo(f"scheduler exiting: {reason}")
                    atomic_write(self.org.root / EXIT_FILE, reason + "\n")
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
            from .progress import _human_items

            self._emit("scheduler.heartbeat", running=sorted(r.run_id for r in self.runs.values()),
                       runnable=len(self._runnable()), waiting_on_you=len(_human_items(self.org)))
        if self._pruned_at is None or now - self._pruned_at >= 86400:
            self._pruned_at = now
            removed = telemetry.prune(self.org.root, config_number(cfg, "events_keep_days", int))
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
        raw = self.org.ledger("failures")
        clean = {k: v for k, v in raw.items() if isinstance(v, int) and not isinstance(v, bool)} if isinstance(raw, dict) else {}
        if clean != raw:
            self.org.save_ledger("failures", clean)
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
        out = []
        for a in self.org.agents():
            if a in self.runs or a in self._blocked or not self.org.unread(a):
                continue
            reason = self.org.paused(a)
            if reason == "budget" and (self.org.budget(a) or 0) > 0:
                reason = None
            if not reason and (self.org.budget(a) or 0) > 0:
                out.append(a)
        return out

    def _launch(self, max_runs: int | None) -> None:
        cfg = self.org.config
        for addr in self.org.agents():
            if len(self.runs) >= config_number(cfg, "max_parallel", int):
                return
            if max_runs is not None and self.total_runs >= max_runs:
                return
            if addr in self.runs or addr in self._blocked or not self.org.unread(addr):
                continue
            reason = self.org.paused(addr)
            budget = self.org.budget(addr) or 0
            if reason == "budget" and budget > 0:
                self.org.resume(addr, "budget is back", by="runtime")
                reason = None
            if reason:
                continue
            if budget <= 0:
                self.org.pause(addr, "budget", by="runtime")
                waiting = [m.trace for m in self.org.messages(addr, "inbox")]
                self.org.notify(self.org.parent(addr) or ROOT, f"{addr} is out of budget",
                                templates.notice_budget(addr, self.org.unread(addr)), trace=telemetry.single(waiting))
                self.echo(f"{addr}: out of budget, paused, parent notified")
                continue
            self._start(addr)

    def _start(self, addr: str) -> None:
        batch = self.org.begin_run(addr)
        budget_before = self.org.budget(addr)  # before the run log exists: that is what consumes the run
        log = self.org.start_run_log(addr)
        run_id = run_id_of(addr, log)
        traces = sorted({m.trace for m in batch if m.trace})
        self.total_runs += 1
        prompt = self.org.run_prompt(addr, batch)
        logf = self.org.runtime.run_log_writer.open_sink(log)
        strays = self._guard_value("stray check", lambda: _stray_probe(self.org, addr))
        try:
            logf.write(log_header(addr, len(batch), (m.sender for m in batch)))  # health tells runtime-only runs apart by the senders
            cmd, cwd, env = self.runner(self.org, addr, prompt)
            env = {**env, "ORG_RUN_ID": run_id}  # the agent's MCP server tags its events with it
            logf.write(log_invocation(cwd, cmd))
            logf.write(log_prompt(prompt))
            logf.flush()
            with tempfile.TemporaryFile() as stdin:  # a file, not a pipe: no deadlock if the child never reads it
                stdin.write(prompt.encode("utf-8"))
                stdin.seek(0)
                # Its own session/process group, so a timeout or shutdown can take the tool subprocesses along.
                proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=stdin, stdout=logf,
                                        stderr=subprocess.STDOUT, text=True, start_new_session=True)
        except Exception as exc:  # e.g. kiro-cli missing: count it as a failed run
            logf.write(log_failed_start(exc))
            logf.close()
            self.org.end_run(addr, ok=False)
            self._emit_run_start(addr, run_id, batch, traces, None, budget_before)
            self._emit("run.end", agent=addr, run=run_id, ok=False, exit_code=None, duration_ms=0, timed_out=False,
                       killed=False, budget_after=self.org.budget(addr),
                       error=telemetry.clip(f"failed to start: {exc}", telemetry.ERROR_MAX))
            self._failed(addr, log, traces)
            return
        self.runs[addr] = Run(addr, proc, log, logf, time.time(), len(batch), strays, run_id, tuple(traces), budget_before)
        self._emit_run_start(addr, run_id, batch, traces, proc.pid, budget_before)
        self._guard("run record", lambda: self._record_run(addr, self.runs[addr]))
        self.echo(f"{addr}: started run ({len(batch)} message(s))")

    def _emit_run_start(self, addr: str, run_id: str, batch, traces: list, pid: int | None, budget_before) -> None:
        self._emit("run.start", agent=addr, run=run_id, trace=telemetry.single(traces), batch=[m.id for m in batch],
                   traces=traces, child_pid=pid, pgid=pid, model=self.org.model_for(addr),
                   budget_before=budget_before)

    def _emit_run_end(self, run: Run, code, error: str | None = None) -> None:
        """The ``run.end`` event; ``error`` None = derived from the exit code."""
        ok = code == 0 and not run.killed
        if error is None and not ok:
            error = f"exit code {code}"
        self._emit("run.end", agent=run.addr, run=run.run_id, trace=telemetry.single(run.traces), ok=ok, exit_code=code,
                   duration_ms=int((time.time() - run.started) * 1000), timed_out=run.timed_out, killed=run.killed,
                   budget_after=self.org.budget(run.addr) if self.org.exists(run.addr) else None,
                   error=telemetry.clip(error, telemetry.ERROR_MAX) if error else None)

    def _reap(self) -> None:
        timeout = config_number(self.org.config, "run_timeout")
        for addr, run in list(self.runs.items()):
            code = run.proc.poll()
            why = None
            if code is None and time.time() - run.started > timeout:
                _signal_group(run.proc, signal.SIGKILL)
                code = run.proc.wait()
                run.logf.write(log_timeout(timeout))
                run.killed = run.timed_out = True
                why = f"timed out: killed after {timeout:.0f}s"
            elif code is None and not self.org.exists(addr):  # retired mid-run: nobody will read its output
                _signal_group(run.proc, signal.SIGKILL)
                code = run.proc.wait()
                run.logf.write(log_retired())
                run.killed = True
                why = "killed: the agent was retired during its run"
            if code is None:
                continue
            elapsed = time.time() - run.started
            run.logf.write(log_exit(code, elapsed))
            self._guard("stray check", lambda: self._check_strays(run))
            run.logf.close()
            del self.runs[addr]
            self._guard("run record", lambda: self.org.runtime.run_registry.forget(addr))
            ok = code == 0
            if not self.org.exists(addr):  # retired while the run was in flight: nothing left to settle
                self._emit_run_end(run, code, why or ("agent retired during its run" if not ok else None))
                self.echo(f"{addr}: was retired during its run (exit {code}); nothing to settle")
                self.org.commit(f"{addr}: run ended after retirement (exit {code})")
                continue
            self.org.end_run(addr, ok)
            self._emit_run_end(run, code, why)
            if ok:
                self.org.clear_failures(addr)
                self.echo(f"{addr}: run finished in {elapsed:.0f}s")
            else:
                self._failed(addr, run.log, run.traces)
            rel = run.log.relative_to(self.org.root)
            self.org.commit(f"{addr}: run {'ok' if ok else f'failed ({code})'}, {run.batch} message(s) [{rel}]")

    def _guard_value(self, phase: str, fn: Callable[[], dict]) -> dict | None:
        """``fn()`` for a best-effort probe: None (and one log line per distinct error) if it fails."""
        out: list[dict] = []
        self._guard(phase, lambda: out.append(fn()))
        return out[0] if out else None

    def _check_strays(self, run: Run) -> None:
        """After a run: did a built-in ``write`` put org files (the agent's MEMORY.md, its ``<address>/`` tree) into its
        workspace? Warn in the run log and the scheduler output, and remember it so the agent's next prompt says so once.
        Nothing is moved or deleted."""
        if run.strays is None:
            return
        found = self.org.runtime.stray_probe.found_since(run.strays, _stray_probe(self.org, run.addr))
        if not found:
            return
        rel = ", ".join(found[:5])
        run.logf.write(log_note(f"warning: {run.addr} created org files in its workspace with the built-in `write` "
                                f"(not in the org, so they are not its memory): {rel}"))
        self.echo(f"{run.addr}: warning: org files in its workspace (built-in write shadows orgmcp write?): {rel}")
        self.org.runtime.stray_registry.record(run.addr, found)  # told once per agent: later strays are only logged

    def _failed(self, addr: str, log: Path, traces=()) -> None:
        n = self.org.record_failure(addr)
        self._emit("agent.failure", agent=addr, count=n, trace=telemetry.single(traces))
        self.echo(f"{addr}: run failed ({n} in a row), log: {log}")
        if n >= config_number(self.org.config, "max_failures", int):
            self.org.pause(addr, "failures", by="runtime")
            rel = str(log.relative_to(self.org.root))
            parent = self.org.parent(addr) or ROOT
            trace = telemetry.single(traces)
            self.org.notify(parent, f"{addr} keeps failing",
                            templates.notice_failures(addr, n, rel, to_human=parent == ROOT), trace=trace)
            if parent != ROOT:  # a human has to look at crashes
                self.org.notify(ROOT, f"{addr} keeps failing", templates.notice_failures(addr, n, rel), trace=trace)

    # --------------------------------------------------------------- reviews

    def _check_review(self) -> None:
        """Start a health review when one is due (see ``review.review_if_due``)."""
        done = review.review_if_due(self.org, datetime.fromtimestamp(self.clock(), timezone.utc))
        if done and done.notes:
            self.echo(f"health review: {done.flagged} flagged, told {', '.join(n.to for n in done.notes)}")

    # ---------------------------------------------------------------- stalls

    def _check_stalls(self) -> None:
        """Climb the escalation ladder for every open task whose assignee has gone quiet.

        Stalled = assignee not running, no unread mail, not paused, not waiting on delegated work, and
        ``stall_after`` seconds since the latest of: the task's creation, the assignee's last run, the previous
        step. Steps: remind the assignee, then tell the assigner, then each ancestor in turn up to root.
        """
        after, now = config_number(self.org.config, "stall_after"), self.clock()
        loaded = self.org.ledger("nudges")  # task id -> {"step": last step taken, "at": when}
        ledger = _nudge_entries(loaded)
        kept: dict[str, dict] = {}  # entries of tasks that are still open
        agents = self.org.agents()
        for gone in set(self._task_memo) - set(agents):
            del self._task_memo[gone]
        for addr in agents:
            tasks = self._task_view(addr, "open_tasks")
            stuck = bool(tasks) and not (
                self.org.running(addr) or self.org.unread(addr) or self.org.paused(addr)
                or self._task_view(addr, "outstanding")
            )
            for task in tasks:
                last = ledger.get(task.id)
                if last:
                    kept[task.id] = last
                if not stuck:
                    continue
                chain = self._chain(addr, task)
                step = last["step"] + 1 if last else 0
                if step >= len(chain):  # root has been told: nothing further up
                    continue
                since = max(self._created(task), self._last_run_end(addr), last["at"] if last else 0)
                if now - since < after:
                    continue
                if step == 0:
                    self.org.notify(addr, f"reminder: {task.title}", templates.notice_nudge(task.id, task.title),
                                    trace=task.trace)
                    self.echo(f"{addr}: reminded about open task {task.id}")
                else:
                    self.org.notify(chain[step], f"stalled: {task.title}",
                                    templates.notice_stalled(addr, task.id, task.title, chain[:step]), trace=task.trace)
                    self.echo(f"{addr}: stalled on {task.id}, told {chain[step]}")
                self._emit("stall.nudge", trace=task.trace, task=task.id, to=chain[step] if step else addr, step=step)
                kept[task.id] = {"step": step, "at": now}
        if kept != loaded:
            self.org.save_ledger("nudges", kept)

    def _task_view(self, addr: str, view: str) -> list:
        """``org.open_tasks`` / ``org.outstanding`` of an agent, recomputed only when its set of message files changes.

        Messages are immutable and named by id, so the file names of an agent's mailboxes (a message moving from
        inbox to inflight to read stays the same message) determine both views. An idle tick therefore lists a few
        directories instead of parsing every message ever received or sent.
        """
        d = self.org.dir(addr)

        def names(*boxes):
            out = set()
            for box in boxes:
                try:
                    out.update(n for n in os.listdir(d / box) if n.endswith(".md") and not n.startswith("."))
                except OSError:
                    pass
            return frozenset(out)

        fingerprint = (names("inbox", "inflight", "read"), names("sent"))
        cached = self._task_memo.get(addr)
        if cached is None or cached[0] != fingerprint:
            cached = self._task_memo[addr] = (fingerprint, {})
        if view not in cached[1]:
            cached[1][view] = getattr(self.org, view)(addr)
        return cached[1][view]

    def _chain(self, addr: str, task) -> list[str]:
        return _chain(self.org, addr, task)

    @staticmethod
    def _created(task) -> float:
        try:
            return datetime.fromisoformat(task.created).timestamp()
        except ValueError:
            return task.path.stat().st_mtime

    def _last_run_end(self, addr: str) -> float:
        return self.org.runtime.run_log_reader.last_end(addr)


def _stray_probe(org: Org, addr: str) -> dict:
    """Where an agent's built-in ``write`` leaves org files in its workspace, and what is there now (``strays.StrayProbe.probe``).

    Kept as the module's patch point for the tests until D-sched-1 moves the stray check out of the scheduler."""
    return org.runtime.stray_probe.probe(addr)


def nothing_to_do(org: Org) -> bool:
    """Would an until-done scheduler exit at once? (root has no open task and no agent has work it could start)"""
    return Scheduler(org, echo=lambda _: None).finished()
