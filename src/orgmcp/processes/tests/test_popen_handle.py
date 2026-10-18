"""``PopenHandle``: which signal call it makes and what it does when the group is gone or not ours (system calls replaced)."""

from __future__ import annotations

import errno
import os
import signal
import subprocess
from typing import cast

import pytest

from orgmcp.processes import ProcessHandle
from orgmcp.processes._spawn import PopenHandle

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-processes")

PID = 4_242_424  # never signalled: os.killpg is replaced in every test that signals


class StubPopen:
    """Just enough of ``subprocess.Popen`` for the handle."""

    def __init__(self, returncode: int | None = None, send_error: type[Exception] | None = None) -> None:
        self.pid = PID
        self.returncode = returncode
        self.sent: list[int] = []
        self.waited: list[float | None] = []
        self._send_error = send_error

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        self.waited.append(timeout)
        return 0 if self.returncode is None else self.returncode

    def send_signal(self, sig: int) -> None:
        self.sent.append(sig)
        if self._send_error:
            raise self._send_error()


def handle_of(stub: StubPopen) -> PopenHandle:
    return PopenHandle(cast("subprocess.Popen[str]", stub))


@pytest.fixture
def killpg(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: calls.append((pgid, sig)))
    return calls


def test_it_is_a_process_handle() -> None:
    assert isinstance(handle_of(StubPopen()), ProcessHandle)


def test_pid_returncode_poll_and_wait_are_the_process(killpg: list[tuple[int, int]]) -> None:
    stub = StubPopen(returncode=5)
    handle = handle_of(stub)
    assert handle.pid == PID and handle.returncode == 5 and handle.poll() == 5
    assert handle.wait(timeout=2.5) == 5 and stub.waited == [2.5]
    assert handle.wait() == 5 and stub.waited == [2.5, None]


def test_the_whole_process_group_is_signalled_by_the_pid_of_the_leader(killpg: list[tuple[int, int]]) -> None:
    stub = StubPopen()
    handle_of(stub).signal_group(signal.SIGTERM)
    assert killpg == [(PID, signal.SIGTERM)] and stub.sent == []


@pytest.mark.parametrize("error", [ProcessLookupError, PermissionError])
def test_when_the_group_is_gone_or_not_ours_the_top_process_is_signalled(
    error: type[OSError], monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(pgid: int, sig: int) -> None:
        raise error()

    monkeypatch.setattr(os, "killpg", refuse)
    stub = StubPopen()
    handle_of(stub).signal_group(signal.SIGKILL)
    assert stub.sent == [signal.SIGKILL]


@pytest.mark.parametrize("group_error", [ProcessLookupError, PermissionError])
@pytest.mark.parametrize("process_error", [ProcessLookupError, PermissionError])
def test_when_the_fallback_is_refused_too_nothing_is_raised(
    group_error: type[OSError], process_error: type[Exception], monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(pgid: int, sig: int) -> None:
        raise group_error()

    monkeypatch.setattr(os, "killpg", refuse)
    stub = StubPopen(send_error=process_error)
    handle_of(stub).signal_group(signal.SIGKILL)
    assert stub.sent == [signal.SIGKILL]


def test_any_other_failure_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def invalid(pgid: int, sig: int) -> None:
        raise OSError(errno.EINVAL, "invalid signal")

    monkeypatch.setattr(os, "killpg", invalid)
    stub = StubPopen()
    with pytest.raises(OSError):
        handle_of(stub).signal_group(999)
    assert stub.sent == []
