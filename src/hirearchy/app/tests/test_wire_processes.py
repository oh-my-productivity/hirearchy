"""The wiring of ``processes``, and the system process table, judge and signaller it makes.

Only processes this test starts are signalled.
"""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from hirearchy.app import wiring
from hirearchy.processes import OrphanJudge, ProcessInspector, ProcessSignaller, ProcessSpawner
from hirearchy.processes._inspect import PsProcessInspector
from hirearchy.processes._judge import PsOrphanJudge
from hirearchy.processes._signal import OsProcessSignaller
from hirearchy.processes._spawn import PopenHandle, PopenProcessSpawner
from hirearchy.processes.testing import FakeProcessTable


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


def test_the_inspector_gives_the_state_and_start_time_of_a_process(child: subprocess.Popen[bytes]) -> None:
    inspector = wiring.open_runtime(Path.cwd()).process_inspector
    info = inspector.info(child.pid)
    assert info is not None and info.state and not info.state.startswith("Z") and info.started
    assert inspector.start_time(child.pid) == info.started


def test_the_inspector_of_a_process_that_does_not_exist_answers_none() -> None:
    gone = subprocess.Popen(["true"])
    gone.wait()
    inspector = wiring.open_runtime(Path.cwd()).process_inspector
    assert inspector.info(gone.pid) is None and inspector.start_time(gone.pid) is None and inspector.command_line(gone.pid) is None


def test_the_command_line_names_the_program(child: subprocess.Popen[bytes]) -> None:
    assert "sleep" in (wiring.open_runtime(Path.cwd()).process_inspector.command_line(child.pid) or "")


def test_the_judge_and_the_signaller_work_on_a_real_run(child: subprocess.Popen[bytes]) -> None:
    runtime = wiring.open_runtime(Path.cwd())
    record = {"pgid": child.pid, "lstart": runtime.process_inspector.start_time(child.pid)}
    assert runtime.orphan_judge.judge(record) == "ours"
    assert runtime.process_signaller.kill_group(child.pid) is True
    assert child.wait(timeout=10) == -signal.SIGKILL
    assert runtime.orphan_judge.judge(record) == "gone"


def test_the_judge_never_calls_the_judging_process_ours() -> None:
    runtime = wiring.open_runtime(Path.cwd())
    assert runtime.orphan_judge.judge({"pgid": os.getpid(), "lstart": runtime.process_inspector.start_time(os.getpid())}) == "foreign"
    assert runtime.orphan_judge.judge({"pgid": os.getpgrp(), "lstart": "x"}) == "foreign"


def test_signal_group_takes_a_popen_and_its_group(child: subprocess.Popen[bytes]) -> None:
    PopenHandle(child).signal_group(signal.SIGTERM)  # (the scheduler's own wrapper of it is gone: the lifecycle signals its handles)
    assert child.wait(timeout=10) == -signal.SIGTERM
