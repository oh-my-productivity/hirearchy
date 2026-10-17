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
from typing import IO, Callable, NamedTuple

from . import review, templates
from .core import ROOT, Org, OrgError, atomic_write
from .health import config_number

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


def ensure_kiro_profile(tools: list[str], agents_dir: Path | None = None, *, org: Org) -> str:
    """Write the scheduler's profile for ``org`` into ``~/.kiro/agents``: only the orgmcp server plus the granted tools.

    The profile is internal to this organization: its MCP server entry carries ``ORG_ROOT`` (this org) and
    ``ORG_REQUIRE_AGENT=1``, so used outside the scheduler (no ``ORG_AGENT``) the server refuses to start instead of
    acting as ``root``. ``ORG_AGENT`` itself is NOT baked in: it comes from the scheduler's process environment
    (assumption: kiro starts MCP servers with its own environment plus the profile's ``env``; if it did not, the
    server would fail closed and the run would fail visibly rather than act as root).

    The directory is resolved when called (not when defined), so ``KIRO_AGENTS_DIR`` can be redirected.
    Profiles of other orgs, and the legacy global ``orgmcp[-tools].json`` files, are never touched.
    """
    agents_dir = Path(agents_dir) if agents_dir is not None else Path(KIRO_AGENTS_DIR)
    tools = sorted(set(tools))
    name = kiro_profile_name(org.root, tools)
    server = {**mcp_server_command(), "env": {"ORG_ROOT": str(org.root), "ORG_REQUIRE_AGENT": "1"}}
    data = templates.kiro_profile(
        name,
        f"internal: used by the orgmcp scheduler for {org.root}; not a general-purpose agent"
        + (f" (built-in tools: {', '.join(tools)})" if tools else ""),
        ["@orgmcp", *tools],
        server,
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
        profile = ensure_kiro_profile(list(meta.get("tools") or []), org=org)
        cmd = [kiro_bin, "chat", "--no-interactive", "--agent", profile]
        model = meta.get("model") or org.config.get("default_model")
        if model:
            cmd += ["--model", str(model)]
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
    logf: IO[str]
    started: float
    batch: int


def _signal_group(proc: subprocess.Popen, sig: int) -> None:
    """Signal a run's whole process group (the run was started in its own session, so pgid == pid)."""
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError):
        try:  # the group is gone (or not ours): fall back to the top process
            proc.send_signal(sig)
        except (ProcessLookupError, PermissionError):
            pass


def _ps(pid: int) -> tuple[str, str] | None:
    """(state, start time) of a process as ``ps`` reports them; None when there is no such process.

    Raises OSError when ``ps`` itself cannot be run (the caller then has to treat the process as unknown).
    """
    env = {**os.environ, "LC_ALL": "C", "TZ": "UTC"}  # the same text for the same process, whatever the caller's locale
    out = subprocess.run(["ps", "-o", "stat=,lstart=", "-p", str(pid)], capture_output=True, text=True,
                         timeout=10, env=env).stdout.split()
    return (out[0], " ".join(out[1:])) if len(out) > 1 else None


def _start_time(pid: int) -> str | None:
    try:
        info = _ps(pid)
    except (OSError, subprocess.SubprocessError):
        return None
    return info[1] if info else None


def judge_orphan(rec: dict) -> str:
    """Is the process recorded for a run of a dead scheduler still ours, and alive?

    * ``gone``: no such process (or a zombie): nothing to kill.
    * ``foreign``: the pid now belongs to something else (other start time, not a session leader): never touched.
    * ``ours``: alive, started at the recorded time, and the leader of its own session and process group, which is
      exactly how the scheduler starts runs. Only then may the group be killed.
    * ``doubt``: alive but unverifiable (no start time recorded, or ``ps`` failed): not killed, and the agent
      does not get a second run while it lives.
    """
    pgid = rec.get("pgid")
    if not isinstance(pgid, int) or isinstance(pgid, bool) or pgid <= 1 or pgid in (os.getpid(), os.getpgrp()):
        return "foreign"
    try:
        info = _ps(pgid)
    except (OSError, subprocess.SubprocessError):
        return "doubt"
    if info is None or info[0].startswith("Z"):
        return "gone"
    recorded = rec.get("lstart")
    if not isinstance(recorded, str) or not recorded:
        return "doubt"
    if recorded != info[1]:
        return "foreign"
    try:
        leader = os.getpgid(pgid) == pgid and os.getsid(pgid) == pgid
    except (ProcessLookupError, PermissionError):
        return "doubt"
    return "ours" if leader else "foreign"


def kill_group(pgid: int, wait: float = 5.0) -> bool:
    """SIGKILL a process group and wait until its leader is gone. True when it is."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            info = _ps(pgid)
        except (OSError, subprocess.SubprocessError):
            return False
        if info is None or info[0].startswith("Z"):
            return True
        time.sleep(0.05)
    return False


# ------------------------------------------------------- start/stop (used by the MCP tools of root)


def ignore_runtime_files(root: Path) -> None:
    """Keep files that change constantly out of the org's git snapshots (``git add -A`` after every run)."""
    path = Path(root) / ".gitignore"
    try:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [line for line in (".runtime/running.json", ".runtime/scheduler.log") if line not in text.split()]
        if missing:
            path.write_text((text.rstrip("\n") + "\n" if text else "") + "\n".join(missing) + "\n", encoding="utf-8")
    except OSError:
        pass


class SchedulerState(NamedTuple):
    """``state``: stopped | running (verified to be this org's scheduler) | unverified (pid alive, not trusted)."""
    state: str
    pid: int | None = None
    since: str | None = None
    detail: str = ""


def scheduler_command(root: Path, max_runs: int | None = None) -> list[str]:
    """``<this venv's orgmcp> --root <org> run [--max-runs N]`` (``python -m orgmcp`` if the script is missing)."""
    script = Path(sys.executable).with_name("orgmcp")
    base = [str(script)] if script.exists() else [sys.executable, "-m", "orgmcp"]
    return [*base, "--root", str(root), "run", *(["--max-runs", str(max_runs)] if max_runs is not None else [])]


def _command_line(pid: int) -> str | None:
    try:
        out = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, timeout=10,
                             env={**os.environ, "LC_ALL": "C"}).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return out.strip() or None


def _looks_like_scheduler_of(command: str, root: Path) -> bool:
    """Does this command line plausibly start the scheduler of the organization at ``root``?

    Needs the ``run`` subcommand and either the org's root path or an ``orgmcp`` program. A ``--root`` that is not
    this org (or cannot be compared, being relative) is a no.
    """
    tokens = command.split()
    names_root = str(root) in command
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
    return "scheduler: stopped"


def start_scheduler(org: Org, max_runs: int | None = None) -> int:
    """Launch a detached scheduler for ``org`` (own session; output to ``.runtime/scheduler.log``). Returns its pid."""
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
    ignore_runtime_files(org.root)
    log = runtime / "scheduler.log"
    env = {**os.environ, "ORG_ROOT": str(org.root), "PYTHONUNBUFFERED": "1"}
    for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
        env.pop(var, None)
    cmd = scheduler_command(org.root, max_runs)
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

    # ------------------------------------------------------------- lifecycle

    def acquire(self) -> None:
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
        self.pidfile.write_text(str(os.getpid()))
        self._ignore_running_ledger()
        self._settle_orphans()  # before recover(): never redeliver a batch while its previous run still lives
        for a in self.org.recover():
            self.echo(f"recovered interrupted run of {a}")

    # --------------------------------------------------- runs of a dead scheduler

    def _running_records(self) -> dict[str, dict]:
        """``.runtime/running.json``: agent -> {pgid, lstart, started, scheduler, log} of every run in flight."""
        raw = self.org.ledger("running")
        return {k: v for k, v in (raw.items() if isinstance(raw, dict) else ()) if isinstance(v, dict)}

    def _record_run(self, addr: str, run: Run) -> None:
        records = self._running_records()
        records[addr] = {
            "pgid": run.proc.pid,  # started in its own session, so pgid == pid
            "lstart": _start_time(run.proc.pid),
            "started": run.started,
            "scheduler": os.getpid(),
            "log": str(run.log.relative_to(self.org.root)),
        }
        self.org.save_ledger("running", records)

    def _forget_run(self, *addrs: str) -> None:
        records = self._running_records()
        if any(records.pop(a, None) is not None for a in addrs):
            self.org.save_ledger("running", records)

    def _ignore_running_ledger(self) -> None:
        """The record changes with every run; keep it out of the org's git snapshots."""
        ignore_runtime_files(self.org.root)

    def _settle_orphans(self) -> None:
        """Kill runs a dead scheduler left behind, and note those that survive.

        Called when a scheduler starts (any record then belongs to a dead one: ``acquire`` has just checked that
        no other scheduler lives) and every tick while some orphan could not be dealt with. A recorded process is
        killed only if ``judge_orphan`` says it is ours; one that is alive but cannot be verified or killed keeps
        its agent from starting a new run until it is gone.
        """
        records = self._running_records()
        keep = {}
        for addr, rec in records.items():
            if addr in self.runs or (self._blocked and addr not in self._blocked):
                keep[addr] = rec
                continue
            verdict = judge_orphan(rec)
            pgid = rec.get("pgid")
            if verdict == "ours":
                if kill_group(pgid):
                    self.echo(f"{addr}: killed the orphaned run of a dead scheduler (process group {pgid})")
                    self._note_in_log(rec, "killed: orphaned run of a scheduler that died")
                    verdict = "gone"
                else:
                    verdict = "doubt"
            if verdict == "foreign":
                self.echo(f"{addr}: recorded process {pgid} is not the run we started; left alone")
            elif verdict == "doubt":
                keep[addr] = rec
                if addr not in self._blocked:
                    self.echo(f"{addr}: an earlier run (process group {pgid}) may still be alive and cannot be "
                              "verified or killed; no new run until it is gone")
                self._blocked.add(addr)
                continue
            self._blocked.discard(addr)
        self._blocked &= set(keep)
        if keep != records:
            self.org.save_ledger("running", keep)

    def _note_in_log(self, rec: dict, text: str) -> None:
        try:
            log = self.org.root / str(rec["log"])
            if log.is_file():
                with open(log, "a", encoding="utf-8") as f:
                    f.write(f"\n# {text}\n")
        except (KeyError, OSError):
            pass

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
            run.logf.write("\n# interrupted by scheduler shutdown\n")
            run.logf.close()
            self.org.end_run(addr, ok=False)
        self._forget_run(*self.runs)
        self.runs.clear()
        self.pidfile.unlink(missing_ok=True)

    def serve(self, until_idle: bool = False, max_runs: int | None = None) -> None:
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
                    break
                time.sleep(config_number(self.org.config, "poll_seconds"))
        except KeyboardInterrupt:
            pass
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
        return bool(self.runs) or (bool(self._runnable()) and (max_runs is None or self.total_runs < max_runs))

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
        else:
            self._phase_errors.pop(phase, None)

    def _resume_funded(self) -> None:
        """Lift a budget pause once budget is back (a refund note arrives without waking anyone)."""
        for addr in self.org.agents():
            if self.org.paused(addr) == "budget" and (self.org.budget(addr) or 0) > 0:
                self.org.resume(addr)
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
                self.org.resume(addr)
                reason = None
            if reason:
                continue
            if budget <= 0:
                self.org.pause(addr, "budget")
                self.org.notify(self.org.parent(addr) or ROOT, f"{addr} is out of budget",
                                templates.notice_budget(addr, self.org.unread(addr)))
                self.echo(f"{addr}: out of budget, paused, parent notified")
                continue
            self._start(addr)

    def _start(self, addr: str) -> None:
        batch = self.org.begin_run(addr)
        log = self.org.start_run_log(addr)
        self.total_runs += 1
        prompt = self.org.run_prompt(addr, batch)
        logf = open(log, "a", encoding="utf-8")
        senders = ", ".join(sorted({m.sender for m in batch}))  # health tells runtime-only runs apart by this
        try:
            logf.write(f"# run of {addr}, {len(batch)} message(s)\n# senders: {senders}\n")
            cmd, cwd, env = self.runner(self.org, addr, prompt)
            logf.write(f"# cwd: {cwd}\n# cmd: {' '.join(cmd)} <prompt on stdin>\n")
            logf.write(f"# ---- prompt ----\n{prompt}\n# ---- output ----\n")
            logf.flush()
            with tempfile.TemporaryFile() as stdin:  # a file, not a pipe: no deadlock if the child never reads it
                stdin.write(prompt.encode("utf-8"))
                stdin.seek(0)
                # Its own session/process group, so a timeout or shutdown can take the tool subprocesses along.
                proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=stdin, stdout=logf,
                                        stderr=subprocess.STDOUT, text=True, start_new_session=True)
        except Exception as exc:  # e.g. kiro-cli missing: count it as a failed run
            logf.write(f"\n# failed to start: {exc}\n")
            logf.close()
            self.org.end_run(addr, ok=False)
            self._failed(addr, log)
            return
        self.runs[addr] = Run(addr, proc, log, logf, time.time(), len(batch))
        self._guard("run record", lambda: self._record_run(addr, self.runs[addr]))
        self.echo(f"{addr}: started run ({len(batch)} message(s))")

    def _reap(self) -> None:
        timeout = config_number(self.org.config, "run_timeout")
        for addr, run in list(self.runs.items()):
            code = run.proc.poll()
            if code is None and time.time() - run.started > timeout:
                _signal_group(run.proc, signal.SIGKILL)
                code = run.proc.wait()
                run.logf.write(f"\n# killed after {timeout:.0f}s timeout\n")
            elif code is None and not self.org.exists(addr):  # retired mid-run: nobody will read its output
                _signal_group(run.proc, signal.SIGKILL)
                code = run.proc.wait()
                run.logf.write("\n# killed: the agent was retired during its run\n")
            if code is None:
                continue
            elapsed = time.time() - run.started
            run.logf.write(f"\n# exit {code} after {elapsed:.0f}s\n")
            run.logf.close()
            del self.runs[addr]
            self._guard("run record", lambda: self._forget_run(addr))
            ok = code == 0
            if not self.org.exists(addr):  # retired while the run was in flight: nothing left to settle
                self.echo(f"{addr}: was retired during its run (exit {code}); nothing to settle")
                self.org.commit(f"{addr}: run ended after retirement (exit {code})")
                continue
            self.org.end_run(addr, ok)
            if ok:
                self.org.clear_failures(addr)
                self.echo(f"{addr}: run finished in {elapsed:.0f}s")
            else:
                self._failed(addr, run.log)
            rel = run.log.relative_to(self.org.root)
            self.org.commit(f"{addr}: run {'ok' if ok else f'failed ({code})'}, {run.batch} message(s) [{rel}]")

    def _failed(self, addr: str, log: Path) -> None:
        n = self.org.record_failure(addr)
        self.echo(f"{addr}: run failed ({n} in a row), log: {log}")
        if n >= config_number(self.org.config, "max_failures", int):
            self.org.pause(addr, "failures")
            rel = str(log.relative_to(self.org.root))
            parent = self.org.parent(addr) or ROOT
            self.org.notify(parent, f"{addr} keeps failing",
                            templates.notice_failures(addr, n, rel, to_human=parent == ROOT))
            if parent != ROOT:  # a human has to look at crashes
                self.org.notify(ROOT, f"{addr} keeps failing", templates.notice_failures(addr, n, rel))

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
                    self.org.notify(addr, f"reminder: {task.title}", templates.notice_nudge(task.id, task.title))
                    self.echo(f"{addr}: reminded about open task {task.id}")
                else:
                    self.org.notify(chain[step], f"stalled: {task.title}",
                                    templates.notice_stalled(addr, task.id, task.title, chain[:step]))
                    self.echo(f"{addr}: stalled on {task.id}, told {chain[step]}")
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
        """Who hears about a stalled task, in order: the assignee, its assigner, then up the tree to root."""
        chain = [addr]
        up = task.sender if self.org.exists(task.sender) else self.org.parent(addr)
        while up:
            chain.append(up)
            up = self.org.parent(up)
        return chain

    @staticmethod
    def _created(task) -> float:
        try:
            return datetime.fromisoformat(task.created).timestamp()
        except ValueError:
            return task.path.stat().st_mtime

    def _last_run_end(self, addr: str) -> float:
        logs = (self.org.dir(addr) / "runs").glob("*.log")
        return max((p.stat().st_mtime for p in logs), default=0.0)
