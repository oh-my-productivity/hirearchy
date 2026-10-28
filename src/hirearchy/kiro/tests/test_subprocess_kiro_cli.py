"""``SubprocessKiroCli`` with real processes (process-only): exit code and output, the environment, closed stdin, the output cap and
the kill of the whole process group on an overrun (docs/design/kiro-runtime-v3.md 13.2)."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path

from hirearchy.kiro import CliResult
from hirearchy.kiro._cli import SubprocessKiroCli


def script(tmp_path: Path, body: str, name: str = "tool") -> str:
    path = tmp_path / name
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_the_exit_code_and_the_output_of_both_streams(tmp_path: Path) -> None:
    result = SubprocessKiroCli().run([script(tmp_path, "echo out\necho err >&2\nexit 3\n")], {}, 10)
    assert isinstance(result, CliResult) and result.code == 3 and set(result.output.split()) == {"out", "err"}


def test_a_missing_binary_is_none(tmp_path: Path) -> None:
    assert SubprocessKiroCli().run([str(tmp_path / "missing")], {}, 10) is None


def test_the_environment_is_exactly_the_one_given(tmp_path: Path) -> None:
    result = SubprocessKiroCli().run([script(tmp_path, 'echo "a=$A b=${B:-unset}"\n')], {"A": "1"}, 10)
    assert result is not None and result.output.strip() == "a=1 b=unset"


def test_stdin_is_closed(tmp_path: Path) -> None:
    started = time.monotonic()
    result = SubprocessKiroCli().run([script(tmp_path, "cat | wc -c | tr -d ' '\n")], {"PATH": os.environ["PATH"]}, 10)
    assert result is not None and result.output.strip() == "0" and time.monotonic() - started < 5


def test_the_output_is_capped_at_64_kb(tmp_path: Path) -> None:
    result = SubprocessKiroCli().run([script(tmp_path, "head -c 300000 /dev/zero | tr '\\0' x\n")], {"PATH": os.environ["PATH"]}, 10)
    assert result is not None and len(result.output) == 64 * 1024


def test_an_overrun_is_none_within_the_timeout_plus_a_second(tmp_path: Path) -> None:
    started = time.monotonic()
    assert SubprocessKiroCli().run([script(tmp_path, "exec sleep 30\n")], {"PATH": os.environ["PATH"]}, 0.5) is None
    assert time.monotonic() - started < 1.5


def test_an_overrun_kills_the_process_group(tmp_path: Path) -> None:
    pid_file = tmp_path / "grandchild.pid"
    body = f'sleep 30 &\necho $! > "{pid_file}"\nwait\n'
    tool = script(tmp_path, body)
    for _ in range(3):
        assert SubprocessKiroCli().run([tool], {"PATH": os.environ["PATH"]}, 2) is None
        if pid_file.exists() and pid_file.read_text(encoding="utf-8").strip():
            break
    assert pid_file.exists() and pid_file.read_text(encoding="utf-8").strip(), "the shell never started its grandchild before the deadline"
    pid = int(pid_file.read_text(encoding="utf-8"))
    for _ in range(40):
        if not alive(pid):
            break
        time.sleep(0.1)
    assert not alive(pid)

