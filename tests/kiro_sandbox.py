"""Safety harness for the tests that use the REAL kiro-cli (marked ``integration``).

Real kiro needs the user's own auth, so these tests run with the real ``$HOME`` and ``PATH`` (``conftest.isolated_kiro``
steps aside for them). What they may touch in ``~/.kiro`` is therefore fenced in here:

* before the test: md5 of every file in ``~/.kiro/agents/`` and of ``~/.kiro/settings/mcp.json`` (hashed, never read
  into a variable that is printed, never shown);
* after the test (pass or fail): delete ONLY the per-org profiles whose JSON ``ORG_ROOT`` is inside the test's tmp dir,
  kill every process whose command line mentions the tmp dir, then assert that the md5s are what they were.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from orgmcp.core import DEFAULT_MODEL, ROOT, Org

MODEL = os.environ.get("ORGMCP_IT_MODEL") or DEFAULT_MODEL
RUN_TIMEOUT = 300  # seconds one agent run may take (the org's run_timeout: the scheduler kills it after that)
SCHEDULER_TIMEOUT = 480  # seconds the whole scheduler process may take before the test kills it


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def kiro_dirs(home: Path | None = None) -> tuple[Path, Path]:
    home = home or Path.home()
    return home / ".kiro" / "agents", home / ".kiro" / "settings" / "mcp.json"


def snapshot(home: Path | None = None) -> dict[str, str | None]:
    """md5 of every file in ``~/.kiro/agents`` and of ``~/.kiro/settings/mcp.json`` (None when it does not exist)."""
    agents, mcp = kiro_dirs(home)
    snap: dict[str, str | None] = {}
    if agents.is_dir():
        for p in sorted(agents.iterdir()):
            if p.is_file():
                snap[str(p)] = md5_of(p)
    snap[str(mcp)] = md5_of(mcp) if mcp.is_file() else None
    return snap


def _org_roots(node) -> list[str]:
    """Every value of an ``ORG_ROOT`` key anywhere in a parsed profile."""
    found: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "ORG_ROOT" and isinstance(v, str):
                found.append(v)
            else:
                found.extend(_org_roots(v))
    elif isinstance(node, list):
        for v in node:
            found.extend(_org_roots(v))
    return found


def inside(path: str | Path, base: Path) -> bool:
    try:
        p = Path(path).expanduser().resolve()
    except OSError:
        return False
    return p == base or base in p.parents


def delete_sandbox_profiles(base: Path, home: Path | None = None) -> list[Path]:
    """Delete the per-org profiles in ``~/.kiro/agents`` whose ``ORG_ROOT`` is inside ``base`` (and only those)."""
    agents, _ = kiro_dirs(home)
    deleted: list[Path] = []
    if not agents.is_dir():
        return deleted
    for p in sorted(agents.glob("*.json")):
        try:
            roots = _org_roots(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
        if roots and all(inside(r, base) for r in roots):
            p.unlink()
            deleted.append(p)
    return deleted


def processes_mentioning(base: Path) -> list[tuple[int, str]]:
    """(pid, command line) of every process, other than this one, whose command line mentions ``base``."""
    needles = {str(base), str(base).removeprefix("/private")}
    out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    mine = {os.getpid(), os.getppid()}
    found = []
    for line in out.splitlines():
        pid_text, _, cmd = line.strip().partition(" ")
        if not pid_text.isdigit() or int(pid_text) in mine:
            continue
        if any(n and n in cmd for n in needles):
            found.append((int(pid_text), cmd.strip()))
    return found


def kill_processes_mentioning(base: Path) -> list[int]:
    """TERM, then KILL, whatever still mentions ``base`` (the process group too, unless it is ours)."""
    killed: list[int] = []
    own_group = os.getpgid(0)
    for sig, grace in ((signal.SIGTERM, 3.0), (signal.SIGKILL, 2.0)):
        procs = processes_mentioning(base)
        if not procs:
            break
        for pid, _ in procs:
            try:
                group = os.getpgid(pid)
                if group != own_group:
                    os.killpg(group, sig)
                else:
                    os.kill(pid, sig)
                killed.append(pid)
            except (ProcessLookupError, PermissionError):
                pass
        deadline = time.time() + grace
        while processes_mentioning(base) and time.time() < deadline:
            time.sleep(0.1)
    return killed


class RealKiro:
    """A sandbox for one integration test: tmp dir, orgs, the scheduler, and the events they leave."""

    def __init__(self, base: Path, model: str = MODEL):
        self.base = base.resolve()
        self.model = model
        self.before = snapshot()

    # ------------------------------------------------------------- building

    def new_org(self, mission: str = "Integration test: tiny tasks, finish quickly.") -> Org:
        return Org.init(self.base / "org", mission, {"poll_seconds": 0.5, "run_timeout": RUN_TIMEOUT})

    def hire(self, org: Org, name: str, role: str, charter: str, **kw) -> str:
        org.hire(ROOT, name, role, charter, model=self.model, **kw)
        return name

    def task(self, org: Org, to: str, title: str, goal: str, acceptance: str, budget: int = 3):
        return org.delegate(ROOT, to, title, goal, acceptance, budget=budget)

    # ------------------------------------------------------------- running

    def run_scheduler(self, org: Org, max_runs: int, timeout: float = SCHEDULER_TIMEOUT) -> str:
        """``orgmcp run --until-idle --max-runs N`` as a child process (own process group) with a hard timeout."""
        script = Path(sys.executable).with_name("orgmcp")
        cmd = [str(script)] if script.exists() else [sys.executable, "-m", "orgmcp"]
        cmd += ["--root", str(org.root), "run", "--until-idle", "--max-runs", str(max_runs)]
        env = {k: v for k, v in os.environ.items() if k not in ("ORG_ROOT", "ORG_AGENT", "ORG_RUN_ID", "ORG_REQUIRE_AGENT")}
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, _ = proc.communicate()
            raise AssertionError(f"scheduler still running after {timeout:.0f}s; killed.\n{out[-2000:]}")
        assert proc.returncode == 0, f"scheduler exited {proc.returncode}:\n{out[-2000:]}"
        return out

    # ------------------------------------------------------------- evidence

    @staticmethod
    def events(org: Org, proc: str) -> list[dict]:
        """Events of every process called ``proc`` (``mcp`` / ``scheduler`` / ``cli``), in file order."""
        found = []
        for f in sorted((org.root / ".runtime" / "events").glob(f"*/{proc}-*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    found.append(json.loads(line))
                except ValueError:
                    pass
        return found

    # ------------------------------------------------------------- cleanup

    def cleanup(self) -> list[str]:
        """Kill leftovers, delete this sandbox's profiles, and return the list of safety violations (empty = clean)."""
        problems: list[str] = []
        kill_processes_mentioning(self.base)
        delete_sandbox_profiles(self.base)
        left = processes_mentioning(self.base)
        if left:
            problems.append(f"processes still mention the sandbox: {[p for p, _ in left]}")
        after = snapshot()
        if after != self.before:
            changed = sorted(k for k in {*self.before, *after} if self.before.get(k) != after.get(k))
            problems.append(f"~/.kiro changed during the test: {changed}")
        return problems


def real_kiro_or_skip() -> str:
    path = shutil.which("kiro-cli")
    if not path:
        import pytest

        pytest.skip("kiro-cli is not on PATH: the real-kiro integration tests need it (and your kiro login)")
    return path
