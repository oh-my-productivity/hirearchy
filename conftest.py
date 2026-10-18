import os
import stat

import pytest

from orgmcp import telemetry
from orgmcp.core import ROOT, Org


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", default=False,
                     help="also run tests marked 'integration' (they use the real kiro-cli / a real LLM)")


def pytest_collection_modifyitems(config, items):
    """Tests marked ``integration`` call a real LLM through kiro-cli: skipped unless asked for
    (``pytest --run-integration`` or ``ORGMCP_RUN_INTEGRATION=1``)."""
    if config.getoption("--run-integration") or os.environ.get("ORGMCP_RUN_INTEGRATION"):
        return
    skip = pytest.mark.skip(reason="real-LLM integration test: pass --run-integration (or ORGMCP_RUN_INTEGRATION=1) to run it")
    for item in items:
        if "integration" not in item.keywords and item.path.parent.name == "integration":
            item.add_marker(pytest.mark.integration)  # whatever lives in tests/integration/ is one: a forgotten mark cannot leak
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def fresh_telemetry():
    """Each test starts with no open event files, no drop counter and the default process name."""
    telemetry.reset()
    yield
    telemetry.reset()


@pytest.fixture(autouse=True)
def isolated_kiro(request, tmp_path_factory, monkeypatch):
    """No unmarked test may touch the real ~/.kiro or start the real kiro-cli.

    * ``orgmcp.scheduler.KIRO_AGENTS_DIR`` and ``$HOME`` point into a throwaway directory;
    * a stub ``kiro-cli`` (exits 0 and appends its argv to ``$KIRO_STUB_LOG``) shadows the real binary on PATH.

    Tests marked ``integration`` get none of this (real kiro needs the user's auth): they must use the ``real_kiro``
    fixture, which fences what they may touch in ``~/.kiro`` (see ``tests/kiro_sandbox.py``).
    """
    if request.node.get_closest_marker("integration"):
        return None
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


@pytest.fixture
def real_kiro(request, tmp_path):
    """Sandbox for a test that uses the REAL kiro-cli (and so a real LLM); only for tests marked ``integration``.

    Skips (does not fail) when ``kiro-cli`` is not on PATH. Afterwards, pass or fail: deletes only the per-org profiles
    whose ``ORG_ROOT`` is inside the test's tmp dir, kills any process that mentions it, and fails the test if the md5
    of any file in ``~/.kiro/agents`` or of ``~/.kiro/settings/mcp.json`` changed.
    """
    import kiro_sandbox

    if not request.node.get_closest_marker("integration"):
        pytest.fail("real_kiro is only for tests marked @pytest.mark.integration (unmarked tests run against a stub kiro-cli)")
    kiro_sandbox.real_kiro_or_skip()
    from orgmcp import scheduler

    assert scheduler.KIRO_AGENTS_DIR == kiro_sandbox.kiro_dirs()[0], "profile directory is not the real ~/.kiro/agents"
    sandbox = kiro_sandbox.RealKiro(tmp_path)
    try:
        yield sandbox
    finally:
        problems = sandbox.cleanup()
    assert not problems, "; ".join(problems)
