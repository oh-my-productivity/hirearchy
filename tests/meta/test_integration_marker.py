import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import testkit
from testkit import kiro_sandbox
from testkit.kiro_world import kiro_home_agents_dir

HERE = testkit.TESTS
INNER = '''
import os, shutil
from pathlib import Path
import pytest

def home_is_real():
    return os.environ["HOME"] == os.environ["REAL_HOME_FOR_TEST"]

def test_unmarked():
    assert not home_is_real()
    assert Path(shutil.which("kiro-cli")).parent.name == "bin" and "kiro-home" in shutil.which("kiro-cli")

@pytest.mark.integration
def test_marked():
    Path(os.environ["MARKER_OUT"], "marked-ran").write_text("x")
    assert home_is_real()
    assert "kiro-home" not in os.environ["PATH"]

@pytest.mark.integration
class TestMarkedClass:
    def test_inside(self):
        Path(os.environ["MARKER_OUT"], "class-ran").write_text("x")
'''
INNER_DIR = '''
import os
from pathlib import Path

def test_unmarked_but_in_integration_dir():
    Path(os.environ["MARKER_OUT"], "dir-ran").write_text("x")
'''


@pytest.fixture
def nested(tmp_path):
    proj = tmp_path / "proj"
    (proj / "integration").mkdir(parents=True)
    shutil.copy(HERE.parent / "conftest.py", proj / "conftest.py")  # the root conftest.py (it moved out of tests/)
    (proj / "test_inner.py").write_text(INNER)
    (proj / "integration" / "test_dir.py").write_text(INNER_DIR)
    out = tmp_path / "out"
    out.mkdir()

    def run(*args, env=None, extra=None):
        for name, text in (extra or {}).items():
            (proj / name).write_text(text)
        base_env = {k: v for k, v in os.environ.items() if k != "HIREARCHY_RUN_INTEGRATION"}
        base_env["PATH"] = os.pathsep.join(d for d in base_env["PATH"].split(os.pathsep) if "kiro-home" not in d)  # the outer stub
        full = {**base_env, "REAL_HOME_FOR_TEST": str(tmp_path / "pretend-real-home"), "HOME": str(tmp_path / "pretend-real-home"),
                "MARKER_OUT": str(out), **(env or {})}
        full["PYTHONPATH"] = os.pathsep.join(filter(None, [str(HERE), full.get("PYTHONPATH", "")]))  # root conftest's plugin: testkit.fixtures
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(proj), *args],
                           cwd=proj, env=full, capture_output=True, text=True, timeout=120)
        return p, sorted(x.name for x in out.iterdir())

    return run


def stub(*argv, stdin=""):
    """The stub ``kiro-cli`` of the fixture, run the way the readiness check and the launcher run kiro."""
    return subprocess.run(["kiro-cli", *argv], input=stdin, capture_output=True, text=True, timeout=30)


def test_unmarked_tests_run_against_the_stub(tmp_path):
    path = shutil.which("kiro-cli")
    assert path and Path(path).parent.parent.name.startswith("kiro-home")
    assert "KIRO_STUB_LOG" in Path(path).read_text()
    assert str(Path.home()).find("kiro-home") != -1
    agents = kiro_home_agents_dir(tmp_path / "org")  # the profiles of an organization live in its own kiro home, below the throwaway HOME
    assert agents.name == "agents" and agents.parent.parent.name == "kiro-home" and str(agents).startswith(str(Path.home()))


def test_the_stub_speaks_the_readiness_commands_of_kiro_cli_2_33():
    version = stub("--version")
    assert (version.returncode, version.stdout.strip()) == (0, "kiro-cli 2.33.0")
    chat_help = stub("chat", "--help")
    assert chat_help.returncode == 0 and all(flag in chat_help.stdout for flag in ("--v3", "--require-mcp-startup", "--output-format"))
    assert stub("whoami").returncode == 0


def test_the_stub_runs_a_v3_chat_that_starts_and_finishes():
    run = stub("chat", "--no-interactive", "--agent", "p", "--model", "m", "--v3", "--require-mcp-startup", "--output-format", "stream-json",
               stdin="the prompt\n")
    events = [json.loads(line) for line in run.stdout.splitlines()]
    assert run.returncode == 0
    assert events[0] == {"type": "runStarted", "data": {"engine": "v3"}}
    assert events[-1]["type"] == "runFinished" and events[-1]["data"]["status"] == "success"


def test_the_stub_writes_what_it_was_asked_to_the_log(isolated_kiro):
    stub("--version")
    stub("chat", "--agent", "p", stdin="x")
    assert (isolated_kiro / "kiro-stub.log").read_text().splitlines() == ["--version", "chat --agent p"]


STATE_VARIABLES = ("HIREARCHY_STATE_DIR", "XDG_STATE_HOME", "KIRO_API_KEY")


def test_the_fixture_clears_the_state_and_key_variables():
    """Readiness takes the ``whoami`` path and the kiro state is below the throwaway HOME, whatever the machine running the tests has set."""
    assert [name for name in STATE_VARIABLES if name in os.environ] == []


INNER_VARIABLES = '''
import os

def test_unmarked_sees_none_of_them():
    assert [name for name in ("HIREARCHY_STATE_DIR", "XDG_STATE_HOME", "KIRO_API_KEY") if name in os.environ] == []
'''


def test_the_fixture_clears_them_even_when_the_process_sets_them(nested):
    p, _ = nested(env={"HIREARCHY_STATE_DIR": "/somewhere/state", "XDG_STATE_HOME": "/somewhere/xdg", "KIRO_API_KEY": "not-a-real-key"},
                  extra={"test_variables.py": INNER_VARIABLES})
    assert p.returncode == 0, p.stdout + p.stderr
    assert "2 passed" in p.stdout and "failed" not in p.stdout, p.stdout


def test_marked_tests_are_skipped_by_default(nested):
    p, ran = nested()
    assert p.returncode == 0, p.stdout + p.stderr
    assert "1 passed" in p.stdout and "3 skipped" in p.stdout, p.stdout
    assert ran == []  # none of the marked tests (marked, marked class, unmarked-in-integration-dir) ran their body


@pytest.mark.parametrize("how", ["flag", "env"])
def test_marked_tests_run_when_asked_and_get_no_stub(nested, how):
    p, ran = nested(*(["--run-integration"] if how == "flag" else []),
                    env={"HIREARCHY_RUN_INTEGRATION": "1"} if how == "env" else None)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "4 passed" in p.stdout, p.stdout
    assert ran == ["class-ran", "dir-ran", "marked-ran"]


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception, reason="real_kiro is only for @integration tests")
def test_real_kiro_fixture_refuses_unmarked_tests(real_kiro):
    pytest.fail("not reached: the fixture fails the setup of an unmarked test")


# ----------------------------------------------------------------- safety harness (no kiro involved)
def write_profile(agents: Path, name: str, org_root: Path) -> Path:
    p = agents / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"name": name, "mcpServers": {"hirearchy": {"env": {"ORG_ROOT": str(org_root)}}}}))
    return p


def test_cleanup_deletes_only_profiles_of_the_sandbox(tmp_path):
    agents = tmp_path / ".kiro" / "agents"
    base = tmp_path / "sandbox"
    base.mkdir()
    mine = write_profile(agents, "mine", base / "org")
    other = write_profile(agents, "other", tmp_path / "somewhere-else" / "org")
    sibling = write_profile(agents, "sibling", tmp_path / "sandbox2" / "org")  # same prefix, different dir
    plain = agents / "plain.json"
    plain.write_text(json.dumps({"name": "plain"}))
    (agents / "broken.json").write_text("{not json")
    deleted = kiro_sandbox.delete_sandbox_profiles(base.resolve(), home=tmp_path)
    assert [p.name for p in deleted] == ["mine.json"]
    assert not mine.exists()
    assert other.exists() and sibling.exists() and plain.exists() and (agents / "broken.json").exists()


def test_snapshot_detects_changes_without_exposing_content(tmp_path):
    agents, mcp = kiro_sandbox.kiro_dirs(tmp_path)
    agents.mkdir(parents=True)
    mcp.parent.mkdir(parents=True)
    (agents / "a.json").write_text("one")
    mcp.write_text("secret-config")
    before = kiro_sandbox.snapshot(tmp_path)
    assert all(v is None or len(v) == 32 for v in before.values())
    assert "secret-config" not in json.dumps(before)
    assert kiro_sandbox.snapshot(tmp_path) == before
    (agents / "a.json").write_text("two")
    assert kiro_sandbox.snapshot(tmp_path) != before


def test_processes_mentioning_the_sandbox_are_found_and_killed(tmp_path):
    base = (tmp_path / "sandbox").resolve()
    base.mkdir()
    proc = subprocess.Popen(["sh", "-c", "sleep 60; :", "--", str(base / "marker")], start_new_session=True)
    try:
        assert any(pid == proc.pid for pid, _ in kiro_sandbox.processes_mentioning(base))
        assert proc.pid in kiro_sandbox.kill_processes_mentioning(base)
        assert proc.wait(timeout=10) != 0
        assert not kiro_sandbox.processes_mentioning(base)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
