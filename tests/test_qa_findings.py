"""QA findings: one minimal reproduction per confirmed defect (see QA_REPORT.md).

Each test asserts the *correct* behavior. They started as ``xfail(strict=True)`` reproductions; every finding is
fixed now, so they run as plain regression tests.
"""

import os
import shutil
import signal
import time
from datetime import timedelta

from orgmcp import review
from orgmcp.app import wiring
from orgmcp.cli import main
from orgmcp.core import ROOT, join_frontmatter, split_frontmatter, utcnow
from orgmcp.health import agent_health, org_health
from orgmcp.mail import MessageParser
from orgmcp.mail.testing import CountingMessageParser
from orgmcp.scheduler import Scheduler

ENG = "ceo/eng"
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
    sched = Scheduler(org, quiet_runner(), echo=lambda _: None)
    sched.acquire()
    try:
        sched.tick()
        assert "ceo" in sched.runs
        sched.runs["ceo"].proc.wait()
        org.retire(ROOT, "ceo", "no longer needed")  # a manager/root may do this at any time
        sched._reap()  # must not raise
        assert not (org.root / "ceo").exists()  # and must not resurrect a ghost directory
    finally:
        sched.release()


def test_qa5_corrupt_nudge_ledger_does_not_crash_tick(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "nudges.json").write_text("[]")  # valid JSON, wrong shape
    Scheduler(org, quiet_runner(), echo=lambda _: None).tick()


def test_qa5_bad_health_threshold_does_not_crash_tick(org):
    configure(org, review_every_seconds=0, health={"idle_after_seconds": "1h"})
    sched = Scheduler(org, quiet_runner(), echo=lambda _: None)
    sched.tick()  # first tick starts the review clock
    sched.tick()  # review is due: must degrade (default threshold / OrgError), not raise TypeError
    org_health(org)  # same for `orgmcp health` / the health tool


def test_qa13_idle_tick_cost_does_not_grow_with_history(org):
    for i in range(40):
        org.send(ROOT, "ceo", f"old note {i}")
    drain(org, "ceo")
    sched = Scheduler(org, quiet_runner(), echo=lambda _: None)
    sched.tick()  # warm up (creates the review ledger)
    counting = CountingMessageParser()
    org.runtime = wiring.open_runtime(org.root, {MessageParser: counting})
    loads = counting.loaded
    sched.tick()
    assert len(loads) < 10, f"an idle tick parsed {len(loads)} message files"


def test_qa16_timeout_kills_the_whole_process_group(org, tmp_path):
    configure(org, run_timeout=1)
    pidfile = tmp_path / "child.pid"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    cmd = ["sh", "-c", f"sleep 47 & echo $! > {pidfile}; wait"]
    sched = Scheduler(org, quiet_runner(cmd), echo=lambda _: None)
    sched.acquire()
    child = None
    try:
        sched.tick()
        deadline = time.time() + 5
        while not (pidfile.exists() and pidfile.read_text().strip()) and time.time() < deadline:
            time.sleep(0.02)
        child = int(pidfile.read_text())
        time.sleep(1.2)
        sched._reap()  # timeout fires here
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


def test_qa7_retiring_agents_does_not_postpone_the_next_review(org):
    runs = org.dir(ENG) / "runs"
    for i in range(5):
        (runs / f"20260101T0000000000{i:02d}.log").touch()
    review.review(org, utcnow())  # ledger: 5 runs so far
    org.retire("ceo", "eng", "done")
    ceo_runs = org.dir("ceo") / "runs"
    for i in range(3):  # three new runs since the review
        (ceo_runs / f"20260102T0000000000{i:02d}.log").touch()
    configure(org, review_every_runs=2, review_every_seconds=10**9)
    assert review.review_if_due(org, utcnow()) is not None


def test_qa8_review_does_not_spend_the_reserve_of_a_manager(org):
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.delegate("ceo", ENG, "work", "g", "a", budget=2)  # budget 1 left, one result outstanding (the reserve)
    assert org.budget("ceo") == 1 and len(org.outstanding("ceo")) == 1
    configure(org, health={"idle_after_seconds": -1})  # ops (never used) is idle -> news for ceo
    result = review.review(org, utcnow() + timedelta(hours=1))
    assert not [n for n in result.notes if n.to == "ceo"], "the note's run would consume the run reserved for eng's result"


def test_qa14_failed_runs_are_not_blamed_as_wasteful(org):
    org.send(ROOT, "ceo", "budget", budget=10)
    runs = org.dir("ceo") / "runs"
    for i in range(5):
        (runs / f"20260101T0000000000{i:02d}.log").write_text(f"# failed to start: kiro-cli not found\n")
    flags = agent_health(org, "ceo", utcnow()).flags
    assert "wasteful" not in flags


def test_qa10_resume_with_trailing_slash_clears_failures(org):
    org.pause("ceo", "failures")
    for _ in range(3):
        org.record_failure("ceo")
    main(["--root", str(org.root), "resume", "ceo/"])
    assert org.ledger("failures").get("ceo", 0) == 0
