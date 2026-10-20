# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from testkit.daemon_world import describe_scheduler, env_server, scheduler_state, start_scheduler, stop_scheduler
from testkit.health_world import with_ports
from testkit.legacy.orgmcp.core import Org, OrgError

from orgmcp.daemon import SchedulerCommand
from orgmcp.daemon.testing import FixedSchedulerCommand, RecordingSchedulerCommand


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def reap_schedulers():
    """Never leave a scheduler behind, whatever a test did."""
    orgs: list[Org] = []
    yield orgs
    for o in orgs:
        try:
            os.kill(int((o.root / ".runtime" / "scheduler.pid").read_text()), signal.SIGKILL)
        except (OSError, ValueError):
            pass


# ------------------------------------------------------------ start / stop
def test_start_and_stop_a_detached_scheduler(org, reap_schedulers, monkeypatch):
    reap_schedulers.append(org)
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = env_server()
    assert "scheduler: stopped" in call(server, "status")
    out = call(server, "start", max_runs=0, until_done=False)  # the real scheduler command; at most 0 runs, so kiro is never started
    pid = int(re.search(r"pid (\d+)", out).group(1))
    assert (org.root / ".runtime" / "scheduler.pid").read_text().strip() == str(pid)
    assert re.search(rf"scheduler: running \(pid {pid}, since \d{{4}}-", call(server, "status"))
    assert f"pid {pid}" in call(server, "whoami")
    assert os.getsid(pid) == pid  # detached: its own session
    assert (org.root / ".runtime" / "scheduler.log").is_file()
    assert ".runtime/scheduler.log" in (org.root / ".gitignore").read_text().split()
    again = fails(server, "start")
    assert "already running" in again and str(pid) in again
    stopped = call(server, "stop")
    assert f"stopped (pid {pid})" in stopped
    deadline = time.time() + 5
    while scheduler_state(org).state != "stopped" and time.time() < deadline:
        time.sleep(0.05)
    assert "scheduler: stopped" in call(server, "status")
    assert call(server, "stop") == "no scheduler is running for this org"
    assert not (org.root / ".runtime" / "scheduler.pid").exists()  # the scheduler shut down cleanly
    call(server, "start", max_runs=0, until_done=False)  # and can be started again
    call(server, "stop")


def test_start_passes_max_runs_and_logs_to_the_runtime_dir(org, reap_schedulers):
    reap_schedulers.append(org)
    seen = {}
    spy = RecordingSchedulerCommand(org.runtime.scheduler_command)
    with_ports(org, {SchedulerCommand: spy})
    start_scheduler(org, max_runs=3)
    seen["cmd"] = spy.issued[0]
    assert seen["cmd"][-5:] == ["--root", str(org.root), "run", "--max-runs", "3"]
    assert Path(seen["cmd"][0]).name == "orgmcp"
    assert "scheduler started" in (org.root / ".runtime" / "scheduler.log").read_text()
    stop_scheduler(org)


def test_start_reports_a_scheduler_that_dies_at_once(org):
    dies = FixedSchedulerCommand([sys.executable, "-c", "import sys; print('boom'); sys.exit(3)"])
    with_ports(org, {SchedulerCommand: dies})
    with pytest.raises(OrgError, match=r"exited at once \(exit 3\)[\s\S]*boom"):
        start_scheduler(org)


def test_start_refuses_a_negative_cap(org):
    with pytest.raises(OrgError, match="max_runs"):
        start_scheduler(org, -1)


@pytest.fixture
def foreign_process():
    proc = subprocess.Popen(["sleep", "60"])
    yield proc
    proc.kill()
    proc.wait()


def test_stop_never_signals_a_foreign_pid(org, foreign_process):
    pidfile = org.root / ".runtime" / "scheduler.pid"
    pidfile.write_text(str(foreign_process.pid))  # stale pidfile whose pid was reused by something else
    assert scheduler_state(org).state == "unverified"
    with pytest.raises(OrgError, match="not verified to be this org's scheduler"):
        stop_scheduler(org)
    with pytest.raises(OrgError, match="not starting"):
        start_scheduler(org)
    assert foreign_process.poll() is None  # not signalled
    assert "not trusted" in describe_scheduler(org) and str(foreign_process.pid) in describe_scheduler(org)
    assert pidfile.read_text() == str(foreign_process.pid)  # and the pidfile was left alone


def test_stop_refuses_a_scheduler_of_another_org(org, tmp_path):
    other = tmp_path / "other-org"
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "--root", str(other), "run"])
    try:
        (org.root / ".runtime" / "scheduler.pid").write_text(str(proc.pid))
        with pytest.raises(OrgError, match="not verified"):
            stop_scheduler(org)
        assert proc.poll() is None
    finally:
        proc.kill()
        proc.wait()


def test_stale_or_garbage_pidfile_means_stopped_and_does_not_block_start(org, reap_schedulers):
    reap_schedulers.append(org)
    pidfile = org.root / ".runtime" / "scheduler.pid"
    dead = subprocess.Popen(["true"])
    dead.wait()
    for text in (str(dead.pid), "garbage", "", "1", "-5"):
        pidfile.write_text(text)
        assert scheduler_state(org).state == "stopped", text
    pidfile.write_text(str(dead.pid))
    start_scheduler(org, max_runs=0)
    assert scheduler_state(org).state == "running"
    stop_scheduler(org)
