import os
import stat

import pytest

from orgmcp import telemetry
from orgmcp.core import ROOT, Org


@pytest.fixture(autouse=True)
def fresh_telemetry():
    """Each test starts with no open event files, no drop counter and the default process name."""
    telemetry.reset()
    yield
    telemetry.reset()


@pytest.fixture(autouse=True)
def isolated_kiro(tmp_path_factory, monkeypatch):
    """No test may touch the real ~/.kiro or start the real kiro-cli.

    * ``orgmcp.scheduler.KIRO_AGENTS_DIR`` and ``$HOME`` point into a throwaway directory;
    * a stub ``kiro-cli`` (exits 0 and appends its argv to ``$KIRO_STUB_LOG``) shadows the real binary on PATH.
    """
    base = tmp_path_factory.mktemp("kiro-home")
    stub_dir = base / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "kiro-cli"
    stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "${KIRO_STUB_LOG:-/dev/null}"\ncat > /dev/null\nexit 0\n')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("HOME", str(base))
    monkeypatch.setenv("KIRO_STUB_LOG", str(base / "kiro-stub.log"))
    monkeypatch.setenv("PATH", f"{stub_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr("orgmcp.scheduler.KIRO_AGENTS_DIR", base / ".kiro" / "agents")
    return base


@pytest.fixture
def org(tmp_path):
    """root -> ceo (manager, can hire) -> eng (worker)."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o
