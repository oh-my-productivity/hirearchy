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
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Callable

from . import templates
from .core import ROOT, Org, OrgError

# (org, agent address, prompt) -> (argv, cwd, env)
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


def ensure_kiro_profile(tools: list[str], agents_dir: Path = KIRO_AGENTS_DIR) -> str:
    """Write ~/.kiro/agents/orgmcp[-tools].json: only the orgmcp server plus the granted built-in tools."""
    tools = sorted(set(tools))
    name = kiro_profile_name(tools)
    data = templates.kiro_profile(
        name,
        "orgmcp organization member" + (f" with {', '.join(tools)}" if tools else ""),
        ["@orgmcp", *tools],
        mcp_server_command(),
    )
    path = agents_dir / f"{name}.json"
    if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != data:
        agents_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return name


def kiro_runner(kiro_bin: str = "kiro-cli") -> Runner:
    def build(org: Org, addr: str, prompt: str) -> tuple[list[str], Path, dict]:
        meta, _ = org.charter(addr)
        profile = ensure_kiro_profile(list(meta.get("tools") or []))
        cmd = [kiro_bin, "chat", "--no-interactive", "--agent", profile]
        model = meta.get("model") or org.config.get("default_model")
        if model:
            cmd += ["--model", str(model)]
        cmd.append(prompt)
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


class Scheduler:
    def __init__(self, org: Org, runner: Runner | None = None, echo: Callable[[str], None] = print):
        self.org = org
        self.runner = runner or kiro_runner()
        self.echo = echo
        self.runs: dict[str, Run] = {}
        self.failures: dict[str, int] = {}
        self.total_runs = 0
        self.pidfile = org.root / ".runtime" / "scheduler.pid"
        self.nudges_file = org.root / ".runtime" / "nudges.json"

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
                time.sleep(float(self.org.config["poll_seconds"]))
        except KeyboardInterrupt:
            pass
        finally:
            self.release()

    # ------------------------------------------------------------------ tick

    def tick(self, max_runs: int | None = None) -> bool:
        """One pass: reap finished runs, start new ones, detect stalls. Returns True if work remains."""
        self._reap()
        if max_runs is None or self.total_runs < max_runs:
            self._launch(max_runs)
        if not self.runs and not self._runnable():
            self._check_stalls()
        return bool(self.runs) or (bool(self._runnable()) and (max_runs is None or self.total_runs < max_runs))

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
            if len(self.runs) >= int(cfg["max_parallel"]):
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
            logf.write(f"# run of {addr}, {len(batch)} message(s)\n# cwd: {cwd}\n# cmd: {' '.join(cmd[:-1])} <prompt>\n")
            logf.write(f"# ---- prompt ----\n{prompt}\n# ---- output ----\n")
            logf.flush()
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=logf,
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
        timeout = float(self.org.config["run_timeout"])
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
            self.org.end_run(addr, ok)
            if ok:
                self.failures[addr] = 0
                self.echo(f"{addr}: run finished in {elapsed:.0f}s")
            else:
                self._failed(addr, run.log)
            rel = run.log.relative_to(self.org.root)
            self.org.commit(f"{addr}: run {'ok' if ok else f'failed ({code})'}, {run.batch} message(s) [{rel}]")

    def _failed(self, addr: str, log: Path) -> None:
        n = self.failures.get(addr, 0) + 1
        self.failures[addr] = n
        self.echo(f"{addr}: run failed ({n} in a row), log: {log}")
        if n >= int(self.org.config["max_failures"]):
            self.org.pause(addr, "failures")
            rel = str(log.relative_to(self.org.root))
            self.org.notify(self.org.parent(addr) or ROOT, f"{addr} keeps failing",
                            templates.notice_failures(addr, n, rel))
            if self.org.parent(addr) != ROOT:  # a human has to look at crashes
                self.org.notify(ROOT, f"{addr} keeps failing", templates.notice_failures(addr, n, rel))

    # ---------------------------------------------------------------- stalls

    def _check_stalls(self) -> None:
        """Nothing can run. Nudge whoever holds an open task they are not waiting on; escalate if that fails."""
        nudges = json.loads(self.nudges_file.read_text()) if self.nudges_file.exists() else {}
        changed = False
        for addr in self.org.agents():
            if self.org.paused(addr) or self.org.outstanding(addr):
                continue
            for task in self.org.open_tasks(addr):
                stage = nudges.get(task.id)
                if stage is None:
                    self.org.notify(addr, f"reminder: {task.title}", templates.notice_nudge(task.id, task.title))
                    nudges[task.id] = "nudged"
                    self.echo(f"{addr}: nudged about open task {task.id}")
                elif stage == "nudged" and self.org.exists(task.sender):
                    self.org.notify(task.sender, f"stalled: {task.title}",
                                    templates.notice_stalled(addr, task.id, task.title))
                    nudges[task.id] = "escalated"
                    self.echo(f"{addr}: stalled on {task.id}, escalated to {task.sender}")
                else:
                    continue
                changed = True
        if changed:
            self.nudges_file.parent.mkdir(parents=True, exist_ok=True)
            self.nudges_file.write_text(json.dumps(nudges, indent=2))
