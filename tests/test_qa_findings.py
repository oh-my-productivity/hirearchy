"""QA findings: one minimal reproduction per confirmed defect (see QA_REPORT.md).

Each test asserts the *correct* behavior. They started as ``xfail(strict=True)`` reproductions; every finding is
fixed now, so they run as plain regression tests.
"""

import os
import shutil
import time
from datetime import timedelta

import pytest

from orgmcp import core, review
from orgmcp.core import ROOT, OrgError, join_frontmatter, split_frontmatter, utcnow
from orgmcp.health import agent_health, org_health
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


def test_qa5_bad_health_threshold_does_not_crash_tick(org):
    configure(org, review_every_seconds=0, health={"idle_after_seconds": "1h"})
    sched = Scheduler(org, quiet_runner(), echo=lambda _: None)
    sched.tick()  # first tick starts the review clock
    sched.tick()  # review is due: must degrade (default threshold / OrgError), not raise TypeError
    org_health(org)  # same for `orgmcp health` / the health tool


# ----------------------------------------------------------- budget and reviews
def test_qa6_retire_returns_unspent_budget_to_the_parent(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=5)
    assert org.budget("ceo") == 5
    org.retire("ceo", "eng", "not needed")
    assert org.budget("ceo") == 10


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


# --------------------------------------------------------------------- core API
def test_qa9_retire_accepts_the_full_address_of_a_direct_report(org):
    assert org.retire("ceo", ENG, "full address, as printed by status/health/review notes") == ENG


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
