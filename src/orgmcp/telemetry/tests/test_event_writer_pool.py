"""``EventWriterPool``: one writer per (organization, process name, pid), the count of what could not be written, and ``reset``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.kernel.testing import FakeClock
from orgmcp.telemetry._pool import DropLog, EventWriterPool, LineWriters

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-telemetry")


def test_the_pool_is_a_pool_of_writers_and_a_drop_log() -> None:
    pool = EventWriterPool(FakeClock())
    assert isinstance(pool, LineWriters) and isinstance(pool, DropLog)


def test_the_writer_of_a_key_is_always_the_same_object() -> None:
    pool = EventWriterPool(FakeClock())
    first = pool.writer("/org", "mcp", 1)
    assert pool.writer("/org", "mcp", 1) is first
    assert len({id(pool.writer(root, proc, pid)) for root, proc, pid in
                [("/org", "mcp", 1), ("/other", "mcp", 1), ("/org", "cli", 1), ("/org", "mcp", 2)]}) == 4


def test_the_file_name_is_the_process_the_pid_and_the_start_in_epoch_milliseconds(tmp_path: Path) -> None:
    clock = FakeClock()
    pool = EventWriterPool(clock)
    writer = pool.writer(str(tmp_path), "scheduler", 4242)
    writer.append({"seq": 0}, "2026-10-18", clock, 5.0, lambda: None)
    (path,) = (tmp_path / ".runtime" / "events" / "2026-10-18").glob("*.jsonl")
    assert path.name == f"scheduler-4242-{int(clock.time() * 1000)}.jsonl"


def test_dropping_counts_and_the_first_one_is_reported_once_on_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    pool = EventWriterPool(FakeClock())
    assert pool.dropped() == 0
    pool.drop(OSError("disk full"))
    pool.drop("again")
    pool.drop(ValueError("third"))
    assert pool.dropped() == 3
    err = capsys.readouterr().err
    assert err == ("orgmcp: the event log is unavailable (disk full); events are being dropped "
                   "(the operation itself is not affected)\n")


def test_a_closed_stderr_does_not_matter(monkeypatch: pytest.MonkeyPatch) -> None:
    class Closed:
        def write(self, text: str) -> int:
            raise ValueError("I/O operation on closed file")

        def flush(self) -> None:
            raise ValueError("I/O operation on closed file")

    monkeypatch.setattr("sys.stderr", Closed())
    pool = EventWriterPool(FakeClock())
    pool.drop("x")
    assert pool.dropped() == 1


def test_reset_closes_every_file_zeroes_the_counter_and_warns_again(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clock = FakeClock()
    pool = EventWriterPool(clock)
    writer = pool.writer(str(tmp_path), "mcp", os.getpid())
    writer.append({"seq": 0}, "2026-10-18", clock, 5.0, lambda: None)
    pool.drop("first")
    capsys.readouterr()
    pool.reset()
    assert pool.dropped() == 0
    assert pool.writer(str(tmp_path), "mcp", os.getpid()) is not writer  # forgotten: the next event opens a new file
    pool.drop("second")
    assert "second" in capsys.readouterr().err
