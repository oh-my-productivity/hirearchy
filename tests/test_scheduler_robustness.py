"""Robustness of the scheduler, health and review code paths (QA_REPORT.md, workstream F2)."""

import os
import pwd
import time
from pathlib import Path

from orgmcp import scheduler as sched_mod
from orgmcp.core import ROOT
from orgmcp.scheduler import Scheduler, ensure_kiro_profile


def real_agent_profiles() -> dict[str, int]:
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)  # the account's home, whatever $HOME says
    return {p.name: p.stat().st_mtime_ns for p in (home / ".kiro" / "agents").glob("orgmcp*.json")}


def run_to_idle(sched, limit=5.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.01)


# ------------------------------------------------------------- test isolation


def test_default_kiro_runner_in_tests_writes_nothing_under_the_real_home(org, isolated_kiro):
    before = real_agent_profiles()
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, echo=lambda _: None)  # the default runner: kiro_runner("kiro-cli")
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    assert (isolated_kiro / ".kiro" / "agents" / "orgmcp.json").is_file()  # the profile went to the sandbox
    assert "--agent orgmcp" in (isolated_kiro / "kiro-stub.log").read_text()  # and the stub, not kiro, ran
    assert real_agent_profiles() == before


def test_ensure_kiro_profile_resolves_the_directory_at_call_time(isolated_kiro, tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setattr(sched_mod, "KIRO_AGENTS_DIR", elsewhere)
    ensure_kiro_profile(["read"])
    assert (elsewhere / "orgmcp-read.json").is_file()
    assert not (isolated_kiro / ".kiro" / "agents" / "orgmcp-read.json").exists()


def test_ensure_kiro_profile_is_atomic_and_idempotent(tmp_path):
    d = tmp_path / "agents"
    ensure_kiro_profile([], d)
    path = d / "orgmcp.json"
    path.write_text("{ not json")  # a corrupt profile is repaired, not fatal
    ensure_kiro_profile([], d)
    assert path.read_text().startswith("{") and '"orgmcp"' in path.read_text()
    mtime = path.stat().st_mtime_ns
    ensure_kiro_profile([], d)
    assert path.stat().st_mtime_ns == mtime  # unchanged profile is not rewritten
    assert [p.name for p in d.iterdir()] == ["orgmcp.json"]  # no temp files left behind


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


def test_malformed_reviews_ledger_restarts_the_review_clock(org):
    write_ledger(org, "reviews", '{"at": 5, "runs": "x", "notified": [1]}')
    sched = Scheduler(org, echo=lambda _: None)
    sched.tick()
    assert json.loads((org.root / ".runtime" / "reviews.json").read_text())["at"]  # a real timestamp again


def test_a_crashing_phase_is_logged_once_and_the_loop_continues(org, monkeypatch):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    messages = []
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=messages.append)

    def boom():
        raise RuntimeError("kaput")

    monkeypatch.setattr(sched, "_check_stalls", boom)
    monkeypatch.setattr(sched, "_check_review", boom)
    sched.tick()
    sched.tick()
    assert "ceo" in sched.runs or org.runs_used("ceo") == 1  # launching still happened
    assert len([m for m in messages if "kaput" in m]) == 2  # once per phase, not once per tick
    sched.release()


@pytest.mark.parametrize("bad", ["1h", None, [], {}, True, float("nan"), "nan", float("inf")])
def test_bad_health_thresholds_fall_back_to_defaults(org, bad):
    configure(org, health={"idle_after_seconds": bad, "max_runs_per_task": bad, "min_runs_for_waste": 7})
    limits = thresholds(org)
    assert limits["idle_after_seconds"] == 86400 and limits["max_runs_per_task"] == 5
    assert limits["min_runs_for_waste"] == 7
    org_health(org)  # no TypeError
    agent_health(org, "ceo")


def test_numeric_string_thresholds_are_accepted(org):
    configure(org, health={"idle_after_seconds": "120", "max_problem_ratio": "0.25"})
    assert thresholds(org)["idle_after_seconds"] == 120 and thresholds(org)["max_problem_ratio"] == 0.25


def test_bad_scheduler_settings_fall_back_to_defaults(org):
    configure(org, run_timeout="soon", max_parallel=None, stall_after="10m", max_failures=[])
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    run_to_idle(sched)
    assert org.runs_used("ceo") == 1
