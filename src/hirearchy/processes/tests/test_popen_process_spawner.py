"""``PopenProcessSpawner`` with real child processes: what the contract suite cannot say (output, input, directory, failure)."""

from __future__ import annotations

import signal
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from hirearchy.processes import ProcessHandle
from hirearchy.processes._spawn import PopenProcessSpawner

from ._support import env


class Spawned:
    """A spawner whose children are all killed (their own groups only) when the test ends."""

    def __init__(self) -> None:
        self.spawner = PopenProcessSpawner()
        self.started: list[ProcessHandle] = []

    def spawn(self, argv: list[str], tmp: Path, *, stdin: object | None = None, stdout: object | None = None) -> ProcessHandle:
        handle = self.spawner.spawn(argv, cwd=tmp, env=env(), stdin=stdin, stdout=stdout)
        self.started.append(handle)
        return handle

    def detached(self, argv: list[str], tmp: Path, log: Path, **extra: str) -> ProcessHandle:
        handle = self.spawner.spawn_detached(argv, cwd=tmp, env={**env(), **extra}, log=log)
        self.started.append(handle)
        return handle

    def close(self) -> None:
        for handle in self.started:
            if handle.poll() is None:
                handle.signal_group(signal.SIGKILL)
                handle.wait(timeout=10)


@pytest.fixture
def spawned() -> Iterator[Spawned]:
    made = Spawned()
    try:
        yield made
    finally:
        made.close()


def test_stdout_and_stderr_land_in_the_same_file_in_order(spawned: Spawned, tmp_path: Path) -> None:
    out = tmp_path / "out.log"
    with open(out, "w", encoding="utf-8") as logf:
        handle = spawned.spawn(["sh", "-c", "echo out; echo err >&2; echo out2"], tmp_path, stdout=logf)
        assert handle.wait(timeout=10) == 0
    assert out.read_text(encoding="utf-8") == "out\nerr\nout2\n"


def test_the_stdin_file_is_what_the_process_reads(spawned: Spawned, tmp_path: Path) -> None:
    out = tmp_path / "out.log"
    with tempfile.TemporaryFile() as stdin, open(out, "w", encoding="utf-8") as logf:
        stdin.write("the prompt\n".encode("utf-8"))
        stdin.seek(0)
        handle = spawned.spawn(["cat"], tmp_path, stdin=stdin, stdout=logf)
        assert handle.wait(timeout=10) == 0
    assert out.read_text(encoding="utf-8") == "the prompt\n"


def test_the_working_directory_and_the_environment_are_the_given_ones(spawned: Spawned, tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    out = tmp_path / "out.log"
    with open(out, "w", encoding="utf-8") as logf:
        handle = spawned.spawner.spawn(
            ["sh", "-c", "pwd -P; echo $HIREARCHY_PROBE"], cwd=work, env={**env(), "HIREARCHY_PROBE": "probe-1"}, stdin=None, stdout=logf
        )
        spawned.started.append(handle)
        assert handle.wait(timeout=10) == 0
    assert out.read_text(encoding="utf-8").splitlines() == [str(work.resolve()), "probe-1"]


def test_the_exit_code_of_a_failing_program_is_returned(spawned: Spawned, tmp_path: Path) -> None:
    assert spawned.spawn(["sh", "-c", "exit 7"], tmp_path).wait(timeout=10) == 7


def test_a_program_that_cannot_be_started_raises_os_error(spawned: Spawned, tmp_path: Path) -> None:
    with pytest.raises(OSError):
        spawned.spawn(["/no/such/program-hirearchy"], tmp_path)


def test_a_detached_process_does_not_read_the_callers_stdin(spawned: Spawned, tmp_path: Path) -> None:
    log = tmp_path / "scheduler.log"
    handle = spawned.detached(["sh", "-c", "cat; echo read-to-the-end"], tmp_path, log)
    assert handle.wait(timeout=10) == 0  # stdin is /dev/null: cat ends at once
    assert log.read_text(encoding="utf-8") == "read-to-the-end\n"


def test_a_detached_process_logs_stdout_and_stderr_and_gets_its_environment(spawned: Spawned, tmp_path: Path) -> None:
    log = tmp_path / "scheduler.log"
    handle = spawned.detached(["sh", "-c", "echo $HIREARCHY_PROBE; echo err >&2"], tmp_path, log, HIREARCHY_PROBE="detached-1")
    assert handle.wait(timeout=10) == 0
    assert log.read_text(encoding="utf-8").splitlines() == ["detached-1", "err"]


def test_a_detached_process_that_cannot_be_started_raises_and_leaves_the_log_usable(spawned: Spawned, tmp_path: Path) -> None:
    log = tmp_path / "scheduler.log"
    log.write_text("# earlier\n", encoding="utf-8")
    with pytest.raises(OSError):
        spawned.detached(["/no/such/program-hirearchy"], tmp_path, log)
    assert log.read_text(encoding="utf-8") == "# earlier\n"
