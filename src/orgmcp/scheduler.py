"""The heartbeat: wake an agent for one fresh, short run whenever its inbox has messages.

One agent runs at most once at a time; different agents run in parallel. A run is a separate
process (kiro-cli by default) whose orgmcp MCP server is bound to the agent via ORG_AGENT.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Callable

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


def kiro_profile_name(tools: list[str]) -> str:
    return "orgmcp" + "".join(f"-{t}" for t in sorted(tools))


def ensure_kiro_profile(tools: list[str], agents_dir: Path | None = None) -> str:
    """Write ~/.kiro/agents/orgmcp[-tools].json: only the orgmcp server plus the granted built-in tools.

    The directory is resolved when called (not when defined), so ``KIRO_AGENTS_DIR`` can be redirected.
    """
    agents_dir = Path(agents_dir) if agents_dir is not None else Path(KIRO_AGENTS_DIR)
    tools = sorted(set(tools))
    name = kiro_profile_name(tools)
    data = templates.kiro_profile(
        name,
        "orgmcp organization member" + (f" with {', '.join(tools)}" if tools else ""),
        ["@orgmcp", *tools],
        mcp_server_command(),
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
        profile = ensure_kiro_profile(list(meta.get("tools") or []))
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
        self.pidfile = org.root / ".runtime" / "scheduler.pid"

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
            if alive:
                raise OrgError(f"a scheduler is already running for this org (pid {pid})")
            self.pidfile.unlink()  # stale
        self.pidfile.write_text(str(os.getpid()))
        for a in self.org.recover():
            self.echo(f"recovered interrupted run of {a}")

    def release(self) -> None:
        for run in list(self.runs.values()):
            run.proc.terminate()
        for addr, run in list(self.runs.items()):
            try:
                run.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                run.proc.kill()
            run.logf.write("\n# interrupted by scheduler shutdown\n")
            run.logf.close()
            self.org.end_run(addr, ok=False)
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

    def _runnable(self) -> list[str]:
        out = []
        for a in self.org.agents():
            if a in self.runs or not self.org.unread(a):
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
            if addr in self.runs or not self.org.unread(addr):
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
        try:
            cmd, cwd, env = self.runner(self.org, addr, prompt)
            logf.write(f"# run of {addr}, {len(batch)} message(s)\n# cwd: {cwd}\n# cmd: {' '.join(cmd)} <prompt on stdin>\n")
            logf.write(f"# ---- prompt ----\n{prompt}\n# ---- output ----\n")
            logf.flush()
            with tempfile.TemporaryFile() as stdin:  # a file, not a pipe: no deadlock if the child never reads it
                stdin.write(prompt.encode("utf-8"))
                stdin.seek(0)
                proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=stdin, stdout=logf,
                                        stderr=subprocess.STDOUT, text=True)
        except Exception as exc:  # e.g. kiro-cli missing: count it as a failed run
            logf.write(f"\n# failed to start: {exc}\n")
            logf.close()
            self.org.end_run(addr, ok=False)
            self._failed(addr, log)
            return
        self.runs[addr] = Run(addr, proc, log, logf, time.time(), len(batch))
        self.echo(f"{addr}: started run ({len(batch)} message(s))")

    def _reap(self) -> None:
        timeout = config_number(self.org.config, "run_timeout")
        for addr, run in list(self.runs.items()):
            code = run.proc.poll()
            if code is None and time.time() - run.started > timeout:
                run.proc.kill()
                code = run.proc.wait()
                run.logf.write(f"\n# killed after {timeout:.0f}s timeout\n")
            if code is None:
                continue
            elapsed = time.time() - run.started
            run.logf.write(f"\n# exit {code} after {elapsed:.0f}s\n")
            run.logf.close()
            del self.runs[addr]
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
            self.org.notify(self.org.parent(addr) or ROOT, f"{addr} keeps failing",
                            templates.notice_failures(addr, n, rel))
            if self.org.parent(addr) != ROOT:  # a human has to look at crashes
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
        for addr in self.org.agents():
            tasks = self.org.open_tasks(addr)
            stuck = bool(tasks) and not (
                self.org.running(addr) or self.org.unread(addr) or self.org.paused(addr) or self.org.outstanding(addr)
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
