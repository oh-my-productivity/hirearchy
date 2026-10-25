# mypy: ignore-errors
"""The scheduler records the SIGTERM and SIGHUP it gets, at once (D-E6-3 C2, design 6.2 and 6.5).

E6's C1 showed a detached scheduler and its run killed during kiro-cli's shutdown with no line left in the event log. The scheduler now writes
``scheduler.signal`` in its signal handler, before any grace period, so a KILL that follows still leaves the record.

A parent process starts the real scheduler (``Org(...).runtime.scheduler_control.start``) as root's MCP server does, with SIGHUP set to its default or
to ignored first (the disposition is inherited through the detach, so it never depends on the runner's). A stub ``kiro-cli`` provides a run that
stays for 30 s and dies on SIGTERM. In the first test the scheduler pauses 30 s between passes, so after the SIGTERM it has not stopped yet when the
SIGKILL comes (a Python sleep goes on after a handler ran): only a record written in the handler survives. No real kiro; about 5 s.
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

from hirearchy.core import ROOT, Org

PARENT = """\
import signal, sys, time
from hirearchy.app import Org

signal.signal(signal.SIGHUP, signal.SIG_IGN if sys.argv[2] == "ignored" else signal.SIG_DFL)
print(Org(sys.argv[1]).runtime.scheduler_control.start(None, True), flush=True)
time.sleep(600)
"""

STUB = """#!/bin/sh
case "$1" in
  --version) echo "kiro-cli 2.33.0" ;;
  whoami) echo "stub user" ;;
  chat)
    if [ "$2" = "--help" ]; then
      printf '%s\\n' "Usage: kiro-cli chat [OPTIONS] [INPUT]" "      --v3" "      --require-mcp-startup" "      --output-format <FORMAT>"
    else
      cat > /dev/null
      printf '%s\\n' '{{"type":"runStarted","data":{{"engine":"v3"}}}}'
      sleep 30
    fi
    ;;
esac
exit 0
"""  # the readiness answers of ``fixtures.STUB``; for ``chat``: start the run and stay in it for 30 s (it dies on SIGTERM)

KEYS = ["v", "ts", "seq", "proc", "pid", "kind", "actor", "run", "trace", "signal", "action", "ppid", "running"]
TYPES = [int, str, int, str, int, str, str, type(None), type(None), str, str, int, list]


def state_of(pid):
    return subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


def gone(pid):
    state = state_of(pid)
    return state == "" or state.startswith("Z")  # a container's init may not reap at once


def events(org, kind):
    out = []
    for file in sorted((org.root / ".runtime" / "events").glob("*/*.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    return [e for e in out if e["kind"] == kind]


def wait_for(condition, limit, what):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        found = condition()
        if found:
            return found
        time.sleep(0.05)
    raise AssertionError(f"gave up after {limit} s waiting for {what}")


class Started:
    """A real scheduler with one run of ``ceo`` in flight; ``close`` kills only the pids this learned."""

    def __init__(self, tmp_path, hup, poll=0.05):
        self.org = Org.init(tmp_path / "org", "Signal", {"poll_seconds": poll})
        self.org.hire(ROOT, "ceo", "Chief executive", "Work.")
        self.org.delegate(ROOT, "ceo", "Signals", "Work.", "none", budget=2)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "kiro-cli"
        stub.write_text(STUB)
        stub.chmod(0o755)
        (tmp_path / "parent.py").write_text(PARENT)
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        self.parent = subprocess.Popen(
            [sys.executable, str(tmp_path / "parent.py"), str(self.org.root), hup], env=env, stdout=subprocess.PIPE, text=True, start_new_session=True,
        )
        self.scheduler, self.group = None, None
        self.scheduler = int(self.parent.stdout.readline())
        start = wait_for(lambda: next((e for e in events(self.org, "run.start") if e["agent"] == "ceo"), None), 15, "the run of ceo to start")
        self.run, self.group = start["run"], start["pgid"]

    def close(self):
        if self.group is not None:
            try:
                os.killpg(self.group, signal.SIGKILL)
            except OSError:
                pass
        if self.scheduler is not None and not gone(self.scheduler):
            try:
                os.kill(self.scheduler, signal.SIGKILL)
            except OSError:
                pass
        try:
            os.kill(self.parent.pid, signal.SIGKILL)
        except OSError:
            pass
        self.parent.wait(timeout=10)
        self.parent.stdout.close()


def test_a_term_then_a_kill_leaves_the_scheduler_signal_line_and_no_scheduler_exit(tmp_path):
    s = Started(tmp_path, "default", poll=30)
    try:
        os.kill(s.scheduler, signal.SIGTERM)
        time.sleep(0.2)
        killed_at = time.time()
        os.kill(s.scheduler, signal.SIGKILL)  # E5 s3's escalation: the kill that follows the TERM
        wait_for(lambda: gone(s.scheduler), 10, f"the scheduler {s.scheduler} to be gone")
        (line,) = events(s.org, "scheduler.signal")
        assert list(line) == KEYS, line
        assert [type(line[k]) for k in KEYS] == TYPES, line
        assert (line["proc"], line["pid"], line["actor"]) == ("scheduler", s.scheduler, "runtime")
        assert (line["signal"], line["action"], line["running"]) == ("SIGTERM", "stop", [s.run]), line
        assert datetime.fromisoformat(line["ts"]).timestamp() < killed_at
        assert events(s.org, "scheduler.exit") == []
    finally:
        s.close()


def test_a_sighup_alone_is_recorded_and_stops_the_scheduler_cleanly(tmp_path):
    s = Started(tmp_path, "default")
    try:
        os.kill(s.scheduler, signal.SIGHUP)
        exit_event = wait_for(lambda: next(iter(events(s.org, "scheduler.exit")), None), 30, "scheduler.exit")
        (line,) = events(s.org, "scheduler.signal")
        assert (line["signal"], line["action"], line["running"]) == ("SIGHUP", "stop", [s.run]), line
        assert exit_event["reason"] == "stopped by SIGHUP", exit_event
    finally:
        s.close()


def test_a_scheduler_started_with_sighup_ignored_records_it_ignored_and_goes_on(tmp_path):
    s = Started(tmp_path, "ignored")
    try:
        os.kill(s.scheduler, signal.SIGHUP)
        line = wait_for(lambda: next(iter(events(s.org, "scheduler.signal")), None), 10, "scheduler.signal")
        assert (line["signal"], line["action"]) == ("SIGHUP", "ignored"), line
        time.sleep(1)
        assert not gone(s.scheduler) and events(s.org, "scheduler.exit") == []
        os.kill(s.scheduler, signal.SIGTERM)
        exit_event = wait_for(lambda: next(iter(events(s.org, "scheduler.exit")), None), 30, "scheduler.exit")
        assert exit_event["reason"] == "stopped by SIGTERM", exit_event
    finally:
        s.close()
