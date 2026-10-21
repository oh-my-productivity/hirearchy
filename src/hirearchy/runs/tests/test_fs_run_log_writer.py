"""``FsRunLogWriter`` and ``FileRunLogSink`` on a real directory: what the contract does not say about files."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, cast

import pytest

from hirearchy.kernel import Clock, OrgPaths
from hirearchy.kernel.testing import FakeClock
from hirearchy.runs import RunLogSink, RunLogWriter
from hirearchy.runs._writer import FileRunLogSink, FsRunLogWriter


class StillClock(FakeClock):
    """A clock that does not move between two readings (what ``core.utcnow`` patched to a constant is)."""

    def now(self) -> datetime:
        return self.t


def writer(root: Path, clock: Clock | None = None) -> FsRunLogWriter:
    return FsRunLogWriter(OrgPaths(root), clock or FakeClock())


def test_the_writer_and_its_sink_implement_the_ports(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    made = writer(tmp_path)
    assert isinstance(made, RunLogWriter) and isinstance(made.open_sink(made.create("ceo")), RunLogSink)


def test_the_runs_directory_is_made_on_demand_and_only_that(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    writer(tmp_path).create("ceo")
    assert sorted(p.name for p in (tmp_path / "ceo").iterdir()) == ["runs"]


def test_the_directory_of_the_agent_is_not_made(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        writer(tmp_path).create("ghost/deeper")
    assert list(tmp_path.iterdir()) == []


def test_a_clock_that_does_not_move_gives_one_log_and_so_one_run(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    still = writer(tmp_path, StillClock(datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc)))
    first, second = still.create("ceo"), still.create("ceo")
    assert first == second and first.name == "20261018T100000000000.log" and len(list((tmp_path / "ceo" / "runs").iterdir())) == 1


def test_a_log_that_exists_keeps_its_content_when_created_again(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    still = writer(tmp_path, StillClock())
    path = still.create("ceo")
    path.write_text("already written\n", encoding="utf-8")
    still.create("ceo")
    assert path.read_text(encoding="utf-8") == "already written\n"


def test_the_log_is_created_with_the_stamp_of_the_clock_of_the_writer(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    clock = FakeClock(datetime(2030, 1, 2, 3, 4, 5, 678901, tzinfo=timezone.utc))
    clock.t = clock.t.replace(microsecond=678900)  # the fake clock adds a microsecond when it is read
    assert writer(tmp_path, clock).create("ceo").name == "20300102T030405678901.log"


def test_a_note_for_a_directory_or_a_missing_file_is_dropped(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "runs" / "x.log").mkdir(parents=True)
    writer(tmp_path).append_note("ceo/runs/x.log", "killed: orphaned")
    writer(tmp_path).append_note("ceo/runs/y.log", "killed: orphaned")
    assert sorted(p.name for p in (tmp_path / "ceo" / "runs").iterdir()) == ["x.log"]


def test_a_note_path_is_taken_below_the_organization(tmp_path: Path) -> None:
    org = tmp_path / "org"
    (org / "ceo" / "runs").mkdir(parents=True)
    (org / "ceo" / "runs" / "x.log").write_text("out", encoding="utf-8")
    writer(org).append_note("ceo/runs/x.log", "note")
    assert (org / "ceo" / "runs" / "x.log").read_text(encoding="utf-8") == "out\n# note\n"


def test_the_sink_is_a_file_a_child_process_can_write_to(tmp_path: Path) -> None:
    """The scheduler passes the sink as the standard output of the agent: it has a file descriptor."""
    (tmp_path / "ceo").mkdir()
    made = writer(tmp_path)
    path = made.create("ceo")
    sink = made.open_sink(path)
    assert isinstance(sink, FileRunLogSink)
    sink.write("# header\n")
    sink.flush()
    proc = subprocess.Popen(
        [sys.executable, "-c", "print('from the child')"], stdout=cast(IO[str], sink), stderr=subprocess.STDOUT, text=True
    )
    assert proc.wait(timeout=30) == 0
    sink.write("# footer\n")
    sink.close()
    assert path.read_text(encoding="utf-8") == "# header\nfrom the child\n# footer\n"


def test_the_sink_opens_in_append_mode_and_utf8(tmp_path: Path) -> None:
    path = tmp_path / "x.log"
    path.write_bytes("é\n".encode("utf-8"))
    sink = FileRunLogSink(path)
    sink.write("→\n")
    sink.close()
    assert path.read_bytes() == "é\n→\n".encode("utf-8")
    assert sink.path == path
