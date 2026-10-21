# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import pwd
import time
from pathlib import Path

from testkit.health_world import Scheduler
from testkit.kiro_world import ensure_kiro_profile, kiro_profile_name, kiro_runner
from testkit.reach.hirearchy.core import ROOT


def real_agent_profiles() -> dict[str, int]:
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)  # the account's home, whatever $HOME says
    return {p.name: p.stat().st_mtime_ns for p in (home / ".kiro" / "agents").glob("hirearchy*.json")}


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
    name = kiro_profile_name(org.root, [])
    assert (isolated_kiro / ".kiro" / "agents" / f"{name}.json").is_file()  # the profile went to the sandbox
    assert f"--agent {name}" in (isolated_kiro / "kiro-stub.log").read_text()  # and the stub, not kiro, ran
    assert real_agent_profiles() == before


def test_ensure_kiro_profile_resolves_the_directory_at_call_time(org, isolated_kiro, tmp_path, monkeypatch):
    home = tmp_path / "elsewhere-home"  # the profile directory is the one of the HOME in force when the profile is written
    elsewhere = home / ".kiro" / "agents"
    monkeypatch.setenv("HOME", str(home))
    name = ensure_kiro_profile(["read"], org=org)
    assert (elsewhere / f"{name}.json").is_file()
    assert not (isolated_kiro / ".kiro" / "agents" / f"{name}.json").exists()


def test_ensure_kiro_profile_is_atomic_and_idempotent(org, tmp_path):
    d = tmp_path / "agents"
    name = ensure_kiro_profile([], d, org=org)
    path = d / f"{name}.json"
    path.write_text("{ not json")  # a corrupt profile is repaired, not fatal
    ensure_kiro_profile([], d, org=org)
    assert path.read_text().startswith("{") and '"hirearchy"' in path.read_text()
    mtime = path.stat().st_mtime_ns
    ensure_kiro_profile([], d, org=org)
    assert path.stat().st_mtime_ns == mtime  # unchanged profile is not rewritten
    assert [p.name for p in d.iterdir()] == [f"{name}.json"]  # no temp files left behind


# ------------------------------------------------------- QA-4: long prompts
def test_prompt_is_delivered_on_stdin_not_in_argv(org, tmp_path):
    out = tmp_path / "stdin.txt"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    argv = ["sh", "-c", f"cat > {out}"]
    sched = Scheduler(org, lambda o, a, p: (argv, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    text = out.read_text()
    assert text.startswith("# hirearchy run: you are `ceo`") and "### task " in text


def test_kiro_command_has_no_prompt_argument(org):
    cmd, _, _ = kiro_runner()(org, "ceo", "THE PROMPT")
    assert "THE PROMPT" not in cmd
