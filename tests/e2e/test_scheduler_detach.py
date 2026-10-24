# mypy: ignore-errors
"""The scheduler outlives the process that starts it (D-E5-3, design 6.4).

E5 s3: kiro-cli ends the tool call of root's MCP server by killing the server's process tree, found by parent pid, and the detached scheduler (started as
the server's child) died with it. The scheduler is now started through an intermediate process and is no descendant of the server.

The test plays that: a parent process starts the real scheduler (``Org(...).runtime.scheduler_control.start``) as root's MCP server does, the test kills the
parent and every descendant it finds by parent pid (SIGTERM, 0.2 s later SIGKILL), and the scheduler and its run still finish. One code path for macOS and
Linux; no real kiro (a stub ``kiro-cli`` runs the stand-in agent), about 5 s.
"""

import json
import os
import shlex
import signal
import subprocess
import sys
import time

import testkit

from hirearchy.core import ROOT, Org

PARENT = """\
import sys, time
from hirearchy.app import Org

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
      sleep 3
      FAKE_MODE=work {python} {fake} >> {log} 2>&1
      printf '%s\\n' '{{"type":"runFinished","data":{{"status":"success","stopReason":"end_turn"}}}}'
    fi
    ;;
esac
exit 0
"""  # the readiness answers of ``fixtures.STUB``; for ``chat``: start the run, work for 3 s, run the stand-in agent, finish the run


def stub_with_a_run(tmp):
    return STUB.format(python=shlex.quote(sys.executable), fake=shlex.quote(str(testkit.FAKE_AGENT)), log=shlex.quote(str(tmp / "agent.log")))


def process_table():
    """{pid: ppid} of every process (``ps -A -o pid=,ppid=``)."""
    out = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True, check=True).stdout
    return {int(a): int(b) for a, b in (line.split() for line in out.splitlines() if line.strip())}


def tree_of(root, table):
    """``root`` and every descendant of it by parent pid, breadth first."""
    found, queue = [root], [root]
    while queue:
        pid = queue.pop(0)
        for child, parent in table.items():
            if parent == pid and child not in found:
                found.append(child)
                queue.append(child)
    return found


def parent_pid(pid):
    out = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return int(out) if out else None


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


def signal_all(pids, sig):
    for pid in pids:
        try:
            os.kill(pid, sig)
        except OSError:
            pass


def test_the_scheduler_and_its_run_finish_after_its_starter_and_every_descendant_are_killed(tmp_path):
    org = Org.init(tmp_path / "org", "Detach", {"poll_seconds": 0.05})
    org.hire(ROOT, "ceo", "Chief executive", "Work.")  # a leaf: its run reports done
    task = org.delegate(ROOT, "ceo", "Reproduction", "Work.", "none", budget=2)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "kiro-cli"
    stub.write_text(stub_with_a_run(tmp_path))
    stub.chmod(0o755)
    (tmp_path / "parent.py").write_text(PARENT)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    parent = subprocess.Popen(
        [sys.executable, str(tmp_path / "parent.py"), str(org.root)], env=env, stdout=subprocess.PIPE, text=True, start_new_session=True,
    )
    scheduler, group, killed = None, None, []
    try:
        scheduler = int(parent.stdout.readline())  # what root's MCP server reports to the assistant
        start = wait_for(lambda: next((e for e in events(org, "run.start") if e["agent"] == "ceo"), None), 15, "the run of ceo to start")
        group = start["pgid"]
        # 4. the scheduler is no descendant of the parent
        table = process_table()
        tree = tree_of(parent.pid, table)
        ppid = parent_pid(scheduler)
        assert ppid not in tree, (
            f"the scheduler {scheduler} is a descendant of its starter: its parent is {ppid}; the starter {parent.pid} and its tree {tree}"
        )
        # what kiro-cli does at the end of the call: SIGTERM to the descendants found by parent pid, 0.2 s later SIGKILL
        killed = list(tree)
        signal_all(killed, signal.SIGTERM)
        time.sleep(0.2)
        signal_all(killed, signal.SIGKILL)
        parent.wait(timeout=10)
        # 5. the run and the scheduler finish by themselves
        end = wait_for(lambda: next((e for e in events(org, "run.end") if e["run"] == start["run"]), None), 30, "the run of ceo to end")
        assert end["ok"] is True, f"the run ended badly: {end}"
        results = [m for m in org.received(ROOT) if m.type == "result" and m.reply_to == task.id]
        assert results and results[0].status == "done", f"the task's result: {results}"
        exit_event = wait_for(lambda: next(iter(events(org, "scheduler.exit")), None), 30, "scheduler.exit")
        assert "finished" in exit_event["reason"], exit_event
        wait_for(lambda: gone(scheduler), 30, f"the scheduler {scheduler} to be gone")
        assert scheduler not in killed, f"the scheduler {scheduler} was among the killed {killed}"
    finally:
        # 6. only the pids this test learned
        if group is not None:
            try:
                os.killpg(group, signal.SIGKILL)
            except OSError:
                pass
        if scheduler is not None and not gone(scheduler):
            signal_all([scheduler], signal.SIGKILL)
        signal_all([parent.pid], signal.SIGKILL)
        parent.wait(timeout=10)
        parent.stdout.close()
