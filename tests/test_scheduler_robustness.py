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
