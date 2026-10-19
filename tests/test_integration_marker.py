"""The default test run never reaches a real LLM.

* unmarked tests run against a stub ``kiro-cli`` and a fake ``$HOME`` (checked here, in-process);
* tests marked ``integration`` (or living in ``tests/integration/``) are skipped unless asked for, and when asked for
  they get the real ``$HOME`` / ``PATH`` (no stub). Checked in a nested pytest run on a throwaway project that reuses
  the root ``conftest.py``, so nothing here can start a real kiro.
* the safety harness (``tests/testkit/kiro_sandbox.py``) deletes only the sandbox's own profiles and detects ~/.kiro changes.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from testkit import kiro_sandbox
from orgmcp import scheduler

HERE = Path(__file__).parent

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

    def run(*args, env=None):
        base_env = {k: v for k, v in os.environ.items() if k != "ORGMCP_RUN_INTEGRATION"}
        base_env["PATH"] = os.pathsep.join(d for d in base_env["PATH"].split(os.pathsep) if "kiro-home" not in d)  # the outer stub
        full = {**base_env, "REAL_HOME_FOR_TEST": str(tmp_path / "pretend-real-home"), "HOME": str(tmp_path / "pretend-real-home"),
                "MARKER_OUT": str(out), **(env or {})}
        full["PYTHONPATH"] = os.pathsep.join(filter(None, [str(HERE), full.get("PYTHONPATH", "")]))  # root conftest's plugin: testkit.fixtures
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(proj), *args],
                           cwd=proj, env=full, capture_output=True, text=True, timeout=120)
        return p, sorted(x.name for x in out.iterdir())

    return run


def test_unmarked_tests_run_against_the_stub():
    stub = shutil.which("kiro-cli")
    assert stub and Path(stub).parent.parent.name.startswith("kiro-home")
    assert "kiro-stub" in Path(stub).read_text() or "KIRO_STUB_LOG" in Path(stub).read_text()
    assert str(Path.home()).find("kiro-home") != -1
    assert str(scheduler.KIRO_AGENTS_DIR).startswith(str(Path.home()))


def test_marked_tests_are_skipped_by_default(nested):
    p, ran = nested()
    assert p.returncode == 0, p.stdout + p.stderr
    assert "1 passed" in p.stdout and "3 skipped" in p.stdout, p.stdout
    assert ran == []  # none of the marked tests (marked, marked class, unmarked-in-integration-dir) ran their body


@pytest.mark.parametrize("how", ["flag", "env"])
def test_marked_tests_run_when_asked_and_get_no_stub(nested, how):
    p, ran = nested(*(["--run-integration"] if how == "flag" else []),
                    env={"ORGMCP_RUN_INTEGRATION": "1"} if how == "env" else None)
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
    p.write_text(json.dumps({"name": name, "mcpServers": {"orgmcp": {"env": {"ORG_ROOT": str(org_root)}}}}))
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
