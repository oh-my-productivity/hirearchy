"""``PsProcessInspector``: how ``ps`` is run (environment, arguments, time limit) and how its text and failures are read."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from typing import Any

import pytest

from hirearchy.kernel.testing import DictEnvironment
from hirearchy.processes import ProcessInfo, ProcessInspector, ProcessTableError
from hirearchy.processes._inspect import PsProcessInspector

CALLS: list[dict[str, Any]] = []


def run_returning(stdout: str) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        CALLS.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    return run


def run_raising(error: Exception) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise error

    return run


@pytest.fixture
def inspector() -> PsProcessInspector:
    CALLS.clear()
    environment = DictEnvironment()
    for name, value in {"PATH": "/probe/bin", "TZ": "Asia/Tokyo", "LC_ALL": "de_DE.UTF-8", "HOME": "/probe/home"}.items():
        environment.set(name, value)
    return PsProcessInspector(environment)


def ps_says(monkeypatch: pytest.MonkeyPatch, stdout: str) -> None:
    monkeypatch.setattr(subprocess, "run", run_returning(stdout))


def test_it_is_a_process_inspector(inspector: PsProcessInspector) -> None:
    assert isinstance(inspector, ProcessInspector)


def test_info_asks_ps_for_state_and_start_time_in_the_c_locale_and_utc(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch) -> None:
    ps_says(monkeypatch, "S     Sun Oct 18 10:00:00 2026\n")
    inspector.info(123)
    (call,) = CALLS
    assert call["args"] == ["ps", "-o", "stat=,lstart=", "-p", "123"]
    assert call["capture_output"] is True and call["text"] is True and call["timeout"] == 10
    assert call["env"]["LC_ALL"] == "C" and call["env"]["TZ"] == "UTC"  # whatever the caller's locale and zone
    assert call["env"]["PATH"] == "/probe/bin" and call["env"]["HOME"] == "/probe/home"  # the rest is the environment's


def test_info_parses_state_and_start_time_and_collapses_blanks(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch) -> None:
    ps_says(monkeypatch, "Ss+   Sun Oct  4 09:05:07 2026\n")
    assert inspector.info(1) == ProcessInfo("Ss+", "Sun Oct 4 09:05:07 2026")


@pytest.mark.parametrize("text", ["", "\n", "S\n"], ids=repr)
def test_info_of_output_without_a_start_time_is_none(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    ps_says(monkeypatch, text)
    assert inspector.info(1) is None


@pytest.mark.parametrize(
    "error", [FileNotFoundError("ps"), PermissionError("ps"), subprocess.TimeoutExpired("ps", 10), subprocess.SubprocessError("x")]
)
def test_info_when_ps_cannot_run_raises_a_process_table_error(
    inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    monkeypatch.setattr(subprocess, "run", run_raising(error))
    with pytest.raises(ProcessTableError):
        inspector.info(1)
    assert inspector.start_time(1) is None and inspector.command_line(1) is None


def test_start_time_is_the_second_part_of_info(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch) -> None:
    ps_says(monkeypatch, "S Sun Oct 18 10:00:00 2026\n")
    assert inspector.start_time(1) == "Sun Oct 18 10:00:00 2026"
    ps_says(monkeypatch, "")
    assert inspector.start_time(1) is None


def test_command_line_asks_ps_for_the_command_in_the_c_locale_and_strips_it(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch) -> None:
    ps_says(monkeypatch, "  /venv/bin/hirearchy --root /org run \n")
    assert inspector.command_line(77) == "/venv/bin/hirearchy --root /org run"
    (call,) = CALLS
    assert call["args"] == ["ps", "-o", "command=", "-p", "77"]
    assert call["timeout"] == 10 and call["env"]["LC_ALL"] == "C" and call["env"]["TZ"] == "Asia/Tokyo"


def test_an_empty_command_line_is_none(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch) -> None:
    ps_says(monkeypatch, "\n")
    assert inspector.command_line(77) is None


def test_a_session_leader_is_a_process_whose_group_and_session_are_its_pid(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(os, "getsid", lambda pid: pid)
    assert inspector.is_session_leader(500) is True
    monkeypatch.setattr(os, "getsid", lambda pid: 1)
    assert inspector.is_session_leader(500) is False
    monkeypatch.setattr(os, "getsid", lambda pid: pid)
    monkeypatch.setattr(os, "getpgid", lambda pid: 1)
    assert inspector.is_session_leader(500) is False


@pytest.mark.parametrize("error", [ProcessLookupError, PermissionError])
def test_a_session_that_cannot_be_looked_up_is_undecidable(
    inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch, error: type[OSError]
) -> None:
    def refuse(pid: int) -> int:
        raise error()

    monkeypatch.setattr(os, "getpgid", refuse)
    assert inspector.is_session_leader(500) is None


def test_alive_follows_signal_zero(inspector: PsProcessInspector, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: seen.append((pid, sig)))
    assert inspector.is_alive(500) is True and seen == [(500, 0)]

    def gone(pid: int, sig: int) -> None:
        raise ProcessLookupError()

    def denied(pid: int, sig: int) -> None:
        raise PermissionError()

    monkeypatch.setattr(os, "kill", gone)
    assert inspector.is_alive(500) is False
    monkeypatch.setattr(os, "kill", denied)
    assert inspector.is_alive(500) is True  # exists, belongs to someone else


def test_own_ids_are_this_process_and_its_group(inspector: PsProcessInspector) -> None:
    assert inspector.own_ids() == (os.getpid(), os.getpgrp())
