"""Robustness of the scheduler, health and review code paths (QA_REPORT.md, workstream F2)."""

import os
import time

from orgmcp.core import ROOT, OrgError, utcnow
from orgmcp.scheduler import Scheduler


def run_to_idle(sched, limit=5.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.01)


# ------------------------------------------------------------ QA-5: fault isolation
import json  # noqa: E402

import pytest  # noqa: E402

from orgmcp.core import join_frontmatter, split_frontmatter  # noqa: E402
from orgmcp.health import agent_health, org_health, thresholds  # noqa: E402


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def write_ledger(org, name, text):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / f"{name}.json").write_text(text)


@pytest.mark.parametrize("name", ["nudges", "reviews", "failures"])
@pytest.mark.parametrize("junk", ["[]", "42", '"x"', "null", "{ broken", '{"a": []}', '{"a": {"step": "x"}}'])
def test_malformed_ledgers_never_kill_tick(org, name, junk):
    configure(org, review_every_seconds=0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    write_ledger(org, name, junk)
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    for _ in range(3):
        sched.tick()
        time.sleep(0.05)
    sched._reap()


def test_a_crashing_phase_is_logged_once_and_the_loop_continues(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    messages = []
    ladder = ScriptedLadder()
    ladder.fail = RuntimeError("kaput")
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=messages.append,
                      ports={StallLadder: ladder, HealthReviewer: FailingHealthReviewer(RuntimeError("kaput"))})
    sched.tick()
    sched.tick()
    assert "ceo" in sched.runs or org.runs_used("ceo") == 1  # launching still happened
    assert len([m for m in messages if "kaput" in m]) == 2  # once per phase, not once per tick
    sched.release()


def test_bad_scheduler_settings_fall_back_to_defaults(org):
    configure(org, run_timeout="soon", max_parallel=None, stall_after="10m", max_failures=[])
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    run_to_idle(sched)
    assert org.runs_used("ceo") == 1


def test_failed_run_of_a_retired_agent_leaves_no_trace(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    messages = []
    sched = Scheduler(org, lambda o, a, p: (["sh", "-c", "exit 3"], o.dir(a), dict(os.environ)), echo=messages.append)
    sched.acquire()
    try:
        sched.tick()
        sched.runs["ceo"].proc.wait()
        org.retire(ROOT, "ceo", "no longer needed")
        sched._reap()
    finally:
        sched.release()
    assert not (org.root / "ceo").exists() and sched.runs == {}
    assert org.ledger("failures") == {} and org.paused("ceo") is None
    assert not [m for m in org.messages(ROOT, "inbox") if "keeps failing" in m.title]
    retired_logs = list((org.root / ".retired").glob("ceo-*/runs/*.log"))
    assert retired_logs and "# exit 3" in retired_logs[0].read_text()  # the log handle was closed and flushed


# --------------------------------------------------- QA-7: monotonic run counter
from orgmcp.review import review_if_due, total_runs  # noqa: E402
# ------------------------------------------------ QA-14: health vs failed runs
from orgmcp.health import agent_health  # noqa: E402,F811


def test_the_scheduler_records_senders_and_exit_in_the_log(org):
    org.notify("ceo", "fyi", "a runtime note")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, lambda o, a, p: (["sh", "-c", "exit 3"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    log = next((org.dir("ceo") / "runs").glob("*.log")).read_text()
    assert "# senders: root, runtime\n" in log and "# exit 3 after" in log
    assert agent_health(org, "ceo", utcnow()).failed_runs >= 1


def test_runtime_only_batch_is_recorded_as_such(org):
    org.send(ROOT, "ceo", "budget", budget=5)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.notify("ceo", "fyi", "a runtime note")
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    assert agent_health(org, "ceo", utcnow()).runtime_runs == 1


# --------------------------------------------------------- QA-13: parse caching
from orgmcp import core  # noqa: E402
from orgmcp.app import wire_processes, wiring  # noqa: E402
from orgmcp.mail import MessageParser  # noqa: E402
from orgmcp.mail.testing import CountingMessageParser  # noqa: E402
from orgmcp.review import HealthReviewer  # noqa: E402
from orgmcp.scheduler.testing import FailingHealthReviewer, ScriptedLadder  # noqa: E402
from orgmcp.stalls import StallLadder  # noqa: E402
from orgmcp.stalls._views import FingerprintTaskViews  # noqa: E402


# ------------------------------------------------- QA-16: process groups
def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_for_pid(pidfile, limit=5.0):
    deadline = time.time() + limit
    while time.time() < deadline:
        if pidfile.exists() and pidfile.read_text().strip():
            return int(pidfile.read_text())
        time.sleep(0.02)
    raise AssertionError("child never started")


def spawn_tree(org, tmp_path, marker):
    pidfile = tmp_path / f"{marker}.pid"
    cmd = ["sh", "-c", f"sleep {marker} & echo $! > {pidfile}; wait"]
    sched = Scheduler(org, lambda o, a, p: (cmd, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    sched.tick()
    return sched, wait_for_pid(pidfile)


def test_shutdown_kills_the_whole_process_group(org, tmp_path):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched, child = spawn_tree(org, tmp_path, "46")
    try:
        sched.release()
        time.sleep(0.2)
        assert not alive(child), "tool subprocess outlived the scheduler"
    finally:
        if alive(child):
            os.kill(child, 9)


def test_retiring_an_agent_mid_run_kills_its_process_group(org, tmp_path):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched, child = spawn_tree(org, tmp_path, "45")
    try:
        org.retire(ROOT, "ceo", "gone")
        sched._reap()
        time.sleep(0.2)
        assert sched.runs == {} and not alive(child) and not (org.root / "ceo").exists()
    finally:
        sched.release()
        if alive(child):
            os.kill(child, 9)


def test_runs_are_started_in_their_own_session(org, tmp_path):
    out = tmp_path / "ids.txt"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    cmd = ["sh", "-c", f"ps -o pid=,pgid= -p $$ > {out}"]
    sched = Scheduler(org, lambda o, a, p: (cmd, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    pid, pgid = map(int, out.read_text().split())
    assert pid == pgid != os.getpgid(0)


# ------------------------------------------------------------------ small extras
def test_acquire_treats_a_pid_owned_by_someone_else_as_alive(org, monkeypatch):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "scheduler.pid").write_text("1")

    def deny(pid, sig):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "kill", deny)
    with pytest.raises(OrgError, match="already running"):
        Scheduler(org, echo=lambda _: None).acquire()
    assert (org.root / ".runtime" / "scheduler.pid").read_text() == "1"  # and the pidfile is left alone


def test_a_stale_or_garbled_pidfile_is_replaced(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "scheduler.pid").write_text("not a pid")
    sched = Scheduler(org, echo=lambda _: None)
    sched.acquire()
    assert (org.root / ".runtime" / "scheduler.pid").read_text() == str(os.getpid())
    sched.release()


def failing_org(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", "ceo/eng", "work", "g", "a", budget=5)
    sched = Scheduler(org, lambda o, a, p: (["sh", "-c", "exit 1"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    configure(org, max_failures=1)
    sched.acquire()
    try:
        deadline = time.time() + 10
        while org.paused("ceo/eng") != "failures" and time.time() < deadline:
            sched.tick()
            time.sleep(0.02)
    finally:
        sched.release()


def test_an_llm_parent_is_told_what_it_can_do_about_a_crashing_report(org):
    failing_org(org)
    parent_note = next(m for m in org.messages("ceo", "inbox", "read") if m.title == "ceo/eng keeps failing")
    assert "delegate" in parent_note.body and "retire" in parent_note.body and "`blocked`" in parent_note.body
    assert "A human will inspect" in parent_note.body and "orgmcp resume" not in parent_note.body
    human_note = next(m for m in org.messages(ROOT, "inbox") if m.title == "ceo/eng keeps failing")
    assert "A human must inspect it and run `orgmcp resume ceo/eng`." in human_note.body


def test_root_as_parent_gets_only_the_human_text(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    configure(org, max_failures=1)
    sched = Scheduler(org, lambda o, a, p: (["sh", "-c", "exit 1"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    notes = [m for m in org.messages(ROOT, "inbox") if m.title == "ceo keeps failing"]
    assert len(notes) == 1 and "orgmcp resume ceo" in notes[0].body
