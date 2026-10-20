# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import shutil
import signal
import time

from testkit.reach.orgmcp.app import wiring
from testkit.reach.orgmcp.core import ROOT, join_frontmatter, split_frontmatter
from testkit.scheduler_loop import loop_over

from orgmcp.mail import MessageParser
from orgmcp.mail.testing import CountingMessageParser
from orgmcp.scheduler._run import LoopMemory

TRUE = shutil.which("true") or "/usr/bin/true"


def quiet_runner(argv=None):
    """A runner that execs a trivial command instead of kiro (no network, no ~/.kiro writes)."""

    def build(org, addr, prompt):
        return (argv or [TRUE]), org.dir(addr), dict(os.environ)

    return build


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def drain(org, addr, ok=True):
    org.begin_run(addr)
    org.end_run(addr, ok=ok)


# ------------------------------------------------------------------- scheduler
def test_qa3_retiring_a_running_agent_does_not_crash_the_scheduler(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = loop_over(org, quiet_runner(), echo=lambda _: None)
    sched.acquire()
    try:
        sched.tick()
        assert "ceo" in sched.state.runs
        sched.state.runs["ceo"].proc.wait()
        org.retire(ROOT, "ceo", "no longer needed")  # a manager/root may do this at any time
        sched.reap()  # must not raise
        assert not (org.root / "ceo").exists()  # and must not resurrect a ghost directory
    finally:
        sched.release()


def test_qa5_corrupt_nudge_ledger_does_not_crash_tick(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "nudges.json").write_text("[]")  # valid JSON, wrong shape
    loop_over(org, quiet_runner(), echo=lambda _: None).tick()


def test_qa13_idle_tick_cost_does_not_grow_with_history(org):
    for i in range(40):
        org.send(ROOT, "ceo", f"old note {i}")
    drain(org, "ceo")
    memory = LoopMemory()
    sched = loop_over(org, quiet_runner(), echo=lambda _: None, memory=memory)
    sched.tick()  # warm up (creates the review ledger)
    counting = CountingMessageParser()
    org.runtime = wiring.open_runtime(org.root, {MessageParser: counting})
    sched = loop_over(org, quiet_runner(), echo=lambda _: None, state=sched.state, memory=memory)  # the same scheduler over the new runtime
    loads = counting.loaded
    sched.tick()
    assert len(loads) < 10, f"an idle tick parsed {len(loads)} message files"


def test_qa16_timeout_kills_the_whole_process_group(org, tmp_path):
    configure(org, run_timeout=1)
    pidfile = tmp_path / "child.pid"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    cmd = ["sh", "-c", f"sleep 47 & echo $! > {pidfile}; wait"]
    sched = loop_over(org, quiet_runner(cmd), echo=lambda _: None)
    sched.acquire()
    child = None
    try:
        sched.tick()
        deadline = time.time() + 5
        while not (pidfile.exists() and pidfile.read_text().strip()) and time.time() < deadline:
            time.sleep(0.02)
        child = int(pidfile.read_text())
        time.sleep(1.2)
        sched.reap()  # timeout fires here
        time.sleep(0.2)
        try:
            os.kill(child, 0)
            alive = True
        except ProcessLookupError:
            alive = False
        assert not alive, "tool subprocess outlived its timed-out run"
    finally:
        sched.release()
        if child:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
