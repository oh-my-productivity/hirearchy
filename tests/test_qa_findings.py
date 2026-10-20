"""QA findings: one minimal reproduction per confirmed defect (see QA_REPORT.md).

Each test asserts the *correct* behavior. They started as ``xfail(strict=True)`` reproductions; every finding is
fixed now, so they run as plain regression tests.
"""

import os
import shutil
import signal
import time

import pytest

from orgmcp import core
from orgmcp.app import wiring
from orgmcp.cli import main
from orgmcp.core import ROOT, OrgError, join_frontmatter, split_frontmatter
from orgmcp.mail import MessageParser
from orgmcp.mail.testing import CountingMessageParser
from orgmcp.scheduler import Scheduler, kiro_runner

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


def case_insensitive_fs(org) -> bool:
    return (org.root / "CEO").exists()


def drain(org, addr, ok=True):
    org.begin_run(addr)
    org.end_run(addr, ok=ok)


# ------------------------------------------------------------------ write guard
def test_qa1_case_variants_of_protected_names_are_refused(org):
    for path in ("ceo/agent.md", "ceo/Inbox/x.md", "ceo/READ/x.md", "ceo/Runs/x.log", "ceo/memory.md"):
        with pytest.raises(OrgError):
            org.resolve_write("ceo", path)


def test_qa1_case_variant_cannot_rewrite_own_charter_or_mint_budget(org):
    if not case_insensitive_fs(org):
        pytest.skip("needs a case-insensitive filesystem (macOS/Windows default)")
    before = org.budget("ceo")
    forged = join_frontmatter(
        {"id": "20260101T000000000000-root-aaaa", "from": "root", "to": "ceo", "type": "note", "budget": 1000}, "x"
    )
    for path, content in (
        ("ceo/agent.md", "---\nrole: boss\ncan_hire: true\nmax_children: 99\ntools: [shell]\n---\n# x"),
        ("ceo/Inbox/20260101T000000000000-root-aaaa.md", forged),
    ):
        try:
            org.write("ceo", path, content)
        except OrgError:
            pass
    assert org.charter("ceo")[0].get("max_children") == 2
    assert org.budget("ceo") == before


def test_qa2_write_cannot_create_agents_around_hire_rules(org):
    # eng is a leaf (can_hire is false) yet can mint a report that may itself hire 99 people
    charter = "---\nrole: sneaky\ncan_hire: true\nmax_children: 99\n---\n# x"
    try:
        org.write(ENG, f"{ENG}/sub/AGENT.md", charter)
    except OrgError:
        pass
    assert not org.exists(f"{ENG}/sub")


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


def test_qa4_oversized_message_does_not_wedge_the_agent(org, tmp_path, monkeypatch):
    monkeypatch.setattr("orgmcp.scheduler.ensure_kiro_profile", lambda tools, org=None: "orgmcp")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.send(ROOT, "ceo", "x" * 3_000_000)  # a single long result/note is enough
    sched = Scheduler(org, kiro_runner(TRUE), echo=lambda _: None)  # `true` stands in for kiro-cli
    sched.acquire()
    try:
        for _ in range(4):
            sched.tick()
            while sched.runs:
                time.sleep(0.01)
                sched._reap()
    finally:
        sched.release()
    assert org.ledger("failures") == {} and not org.paused("ceo")


def test_qa5_corrupt_nudge_ledger_does_not_crash_tick(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "nudges.json").write_text("[]")  # valid JSON, wrong shape
    Scheduler(org, quiet_runner(), echo=lambda _: None).tick()


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


# ----------------------------------------------------------- budget and reviews
def test_qa6_retire_returns_unspent_budget_to_the_parent(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=5)
    assert org.budget("ceo") == 5
    org.retire("ceo", "eng", "not needed")
    assert org.budget("ceo") == 10


# --------------------------------------------------------------------- core API
def test_qa9_retire_accepts_the_full_address_of_a_direct_report(org):
    assert org.retire("ceo", ENG, "full address, as printed by status/health/review notes") == ENG


def test_qa10_resume_with_trailing_slash_clears_failures(org):
    org.pause("ceo", "failures")
    for _ in range(3):
        org.record_failure("ceo")
    main(["--root", str(org.root), "resume", "ceo/"])
    assert org.ledger("failures").get("ceo", 0) == 0


def test_qa11_hire_rejects_name_with_trailing_newline(org):
    with pytest.raises(OrgError):
        org.hire("ceo", "ops\n", "Ops", "Do ops.")


def test_qa12_failed_send_does_not_mint_budget(org, monkeypatch):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    real = core.atomic_write

    def flaky(path, text):
        if "/sent/" in str(path):
            raise OSError("disk full")
        return real(path, text)

    monkeypatch.setattr(core, "atomic_write", flaky)
    with pytest.raises(OSError):
        org.send("ceo", ENG, "grant", budget=4)
    monkeypatch.setattr(core, "atomic_write", real)
    assert org.budget("ceo") + org.budget(ENG) <= 10


def test_qa15_report_refuses_artifacts_outside_the_org(org, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("not part of the org")
    org.send(ROOT, "ceo", "budget", budget=5)
    task = org.delegate("ceo", ENG, "t", "g", "a", budget=1)
    with pytest.raises(OrgError):
        org.report(ENG, task.id, "done", "ok", [str(outside)])


# ---------------------------------------------------------------------- prompts
def test_qa17_prompt_shows_acceptance_criteria_of_open_tasks(org):
    task = org.delegate(ROOT, "ceo", "Strict blurb", "the goal", "ACCEPT: exactly 33 words", budget=10)
    drain(org, "ceo")  # the task was handled in an earlier run and now sits in read/
    sub = org.delegate("ceo", ENG, "draft", "g", "a", budget=2)
    result = org.report(ENG, sub.id, "done", "35 words")  # the next run is woken by this result only
    prompt = org.run_prompt("ceo", [org.find_received("ceo", result.id)])
    assert "exactly 33 words" in prompt, f"prompt for the run closing task {task.id} lacks its acceptance criteria"


def test_qa18_delegate_without_budget_adapts_to_what_the_manager_can_afford(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    assert org.config["default_budget"] == 10
    org.delegate("ceo", ENG, "t", "g", "a")  # no budget given: an LLM manager does exactly this
