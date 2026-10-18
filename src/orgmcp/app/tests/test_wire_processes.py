"""The wiring of ``processes``, and the module-level helpers of ``scheduler.py`` that now delegate to it (patch points stay valid).

Only processes this test starts are signalled.
"""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from orgmcp import scheduler as sched
from orgmcp.app import wire_processes, wiring
from orgmcp.processes import OrphanJudge, ProcessInspector, ProcessSignaller, ProcessSpawner
from orgmcp.processes._inspect import PsProcessInspector
from orgmcp.processes._judge import PsOrphanJudge
from orgmcp.processes._signal import OsProcessSignaller
from orgmcp.processes._spawn import PopenHandle, PopenProcessSpawner
from orgmcp.processes.testing import FakeProcessTable


@pytest.fixture
def child() -> Iterator[subprocess.Popen[bytes]]:
    """A session leader started by the test, killed (it alone) when the test ends."""
    proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
    try:
        yield proc
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


# ----------------------------------------------------------------------------------------------------------------- the wiring


def test_the_runtime_has_the_real_process_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.process_spawner, PopenProcessSpawner)
    assert isinstance(runtime.process_inspector, PsProcessInspector)
    assert isinstance(runtime.process_signaller, OsProcessSignaller)
    assert isinstance(runtime.orphan_judge, PsOrphanJudge)
    assert isinstance(runtime.process_spawner, ProcessSpawner) and isinstance(runtime.process_inspector, ProcessInspector)
    assert isinstance(runtime.process_signaller, ProcessSignaller) and isinstance(runtime.orphan_judge, OrphanJudge)


def test_the_process_ports_are_replaced_by_the_fake_table(tmp_path: Path) -> None:
    table = FakeProcessTable()
    runtime = wiring.open_runtime(
        tmp_path, {ProcessSpawner: table, ProcessInspector: table, ProcessSignaller: table}
    )
    assert runtime.process_spawner is table and runtime.process_inspector is table and runtime.process_signaller is table
    assert isinstance(runtime.orphan_judge, PsOrphanJudge)  # built over the replaced inspector


def test_two_runtimes_do_not_share_process_objects(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).process_inspector is not wiring.open_runtime(tmp_path).process_inspector


def test_adopt_wraps_a_popen_in_a_handle(child: subprocess.Popen[bytes]) -> None:
    handle = wire_processes.adopt(child)  # type: ignore[arg-type]
    assert isinstance(handle, PopenHandle) and handle.pid == child.pid and handle.poll() is None


# ------------------------------------------------------------------------------------------------ scheduler.py still answers


def test_ps_is_the_state_and_start_time_of_a_process(child: subprocess.Popen[bytes]) -> None:
    state, started = sched._ps(child.pid) or ("", "")
    assert state and not state.startswith("Z") and started
    assert sched._start_time(child.pid) == started


def test_ps_of_a_process_that_does_not_exist_is_none() -> None:
    gone = subprocess.Popen(["true"])
    gone.wait()
    assert sched._ps(gone.pid) is None and sched._start_time(gone.pid) is None and sched._command_line(gone.pid) is None


def test_ps_that_cannot_run_raises_os_error_as_it_always_did(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "/nonexistent-orgmcp-bin")
    with pytest.raises(OSError):
        sched._ps(os.getpid())
    assert sched._start_time(os.getpid()) is None and sched._command_line(os.getpid()) is None


def test_the_command_line_names_the_program(child: subprocess.Popen[bytes]) -> None:
    assert "sleep" in (sched._command_line(child.pid) or "")


def test_judge_orphan_and_kill_group_work_on_a_real_run(child: subprocess.Popen[bytes]) -> None:
    record = {"pgid": child.pid, "lstart": sched._start_time(child.pid)}
    assert sched.judge_orphan(record) == "ours"
    assert sched.kill_group(child.pid) is True
    assert child.wait(timeout=10) == -signal.SIGKILL
    assert sched.judge_orphan(record) == "gone"


def test_judge_orphan_never_calls_the_judging_process_ours() -> None:
    assert sched.judge_orphan({"pgid": os.getpid(), "lstart": sched._start_time(os.getpid())}) == "foreign"
    assert sched.judge_orphan({"pgid": os.getpgrp(), "lstart": "x"}) == "foreign"


def test_signal_group_takes_a_popen_and_its_group(child: subprocess.Popen[bytes]) -> None:
    sched._signal_group(child, signal.SIGTERM)
    assert child.wait(timeout=10) == -signal.SIGTERM
