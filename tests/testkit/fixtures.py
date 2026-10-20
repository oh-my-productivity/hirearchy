"""Shared pytest fixtures (registered by the root conftest.py as the ``testkit.fixtures`` plugin).

``isolated_kiro`` and ``fresh_process_resources`` are autouse: no unmarked test touches the real ~/.kiro or starts the real kiro-cli, and each
test starts with the process resources empty (no open event files, no drop counter, the default process name, no cached parse). ``org`` is a ready team; ``real_kiro`` is the sandbox of the (skipped by default) integration tests.
"""

import contextlib
import os
import stat

import pytest

from orgmcp.app import wiring
from orgmcp.core import ROOT, Org
from orgmcp.kernel import TokenSource
from orgmcp.kernel.testing import CounterTokens

from . import process_state
from .clocks import clock_ports


@pytest.fixture(autouse=True)
def process_state_guard(request):
    """A test may patch the process-global state of orgmcp.core / orgmcp.app only through ``monkeypatch``. This fixture is set up before
    ``monkeypatch`` (``isolated_kiro`` lists it first), so it is torn down after it: whatever is still replaced then is put back and fails
    the *leaking* test, by name; without it the damage shows up in whichever test of ``orgmcp.app`` happens to run next."""
    before = process_state.ProcessState.capture()
    yield
    process_state.verify(before, request.node.nodeid)


@pytest.fixture(autouse=True)
def fresh_process_resources():
    """Each test starts with the process resources empty: no open event files, no drop counter, the default process name, no sinks."""
    wiring.process_resources().reset()
    yield
    wiring.process_resources().reset()


@pytest.fixture(autouse=True)
def isolated_kiro(request, tmp_path_factory, process_state_guard, monkeypatch):
    """No unmarked test may touch the real ~/.kiro or start the real kiro-cli.

    * ``orgmcp.scheduler.KIRO_AGENTS_DIR`` and ``$HOME`` point into a throwaway directory;
    * a stub ``kiro-cli`` (exits 0 and appends its argv to ``$KIRO_STUB_LOG``) shadows the real binary on PATH.

    Tests marked ``integration`` get none of this (real kiro needs the user's auth): they must use the ``real_kiro``
    fixture, which fences what they may touch in ``~/.kiro`` (see ``tests/testkit/kiro_sandbox.py``).
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
def process_overrides(request):
    """``process_overrides({Port: fake, ...})``: every runtime opened from now until the end of the test (by the test or by the code under test:
    ``Org(root)``, a CLI command, an MCP tool, the scheduler) starts from these ports; ``open_runtime(root, overrides)`` still wins. The one seam
    that replaces patching module attributes (``wiring.overriding``). Request it BEFORE the fixtures that open an organization (``org``)."""
    with contextlib.ExitStack() as stack:
        yield lambda overrides: stack.enter_context(wiring.overriding(overrides))


@pytest.fixture
def frozen_clock(process_overrides):
    """``frozen_clock(now, events=False)``: the ``Clock`` of every runtime reads ``now`` (a datetime, or a function returning one, called at each reading);
    the time/monotonic/sleep of the clock stay the system's. The events are stamped with the system's time unless ``events`` (the clock of the events is
    a port of its own). Returns ``now`` as a function (``clock()``, and the ``at``/``tick`` it may have)."""

    def freeze(now, events=False):
        reading = now if callable(now) else (lambda: now)
        process_overrides(clock_ports(reading, events))
        return now if callable(now) else reading

    return freeze


@pytest.fixture
def counter_ids(process_overrides):
    """``counter_ids(per_length=False, start=0)``: message ids (and the temp names of atomic writes) count 0000, 0001 ... instead of being random. One
    counter for all lengths by default (the scenarios), one per byte length with ``per_length`` (the golden suite). Returns the ``CounterTokens``."""

    def count(per_length=False, start=0):
        tokens = CounterTokens(per_length, start)
        process_overrides({TokenSource: tokens})
        return tokens

    return count


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
    from . import kiro_sandbox

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
