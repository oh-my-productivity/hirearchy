"""``FileLineWriter``: numbers the lines of one file, opens the day's file when the day changes, and backs off after a failure."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from orgmcp.kernel import JsonObject
from orgmcp.kernel.testing import FakeClock
from orgmcp.telemetry._ports import LineWriter
from orgmcp.telemetry._writer import FileLineWriter

DAY, NEXT_DAY = "2026-10-18", "2026-10-19"


class Fresh:
    """Counts how often the writer says the events directory is new."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


def make(tmp_path: Path) -> tuple[FileLineWriter, Path, FakeClock, Fresh]:
    events = tmp_path / ".runtime" / "events"
    clock = FakeClock()
    return FileLineWriter(str(events), "mcp-1-1", threading.Lock()), events, clock, Fresh()


def lines(path: Path) -> list[JsonObject]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_a_writer_is_a_line_writer(tmp_path: Path) -> None:
    assert isinstance(make(tmp_path)[0], LineWriter)


def test_lines_are_numbered_from_one_in_the_file_of_the_day(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    for i in range(3):
        writer.append({"v": 1, "seq": 0, "i": i}, DAY, clock, 5.0, fresh)
    assert [e["seq"] for e in lines(events / DAY / "mcp-1-1.jsonl")] == [1, 2, 3]


def test_a_new_day_is_a_new_file_and_the_numbering_starts_again(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    writer.append({"seq": 0}, NEXT_DAY, clock, 5.0, fresh)
    writer.append({"seq": 0}, NEXT_DAY, clock, 5.0, fresh)
    assert [e["seq"] for e in lines(events / DAY / "mcp-1-1.jsonl")] == [1, 2]
    assert [e["seq"] for e in lines(events / NEXT_DAY / "mcp-1-1.jsonl")] == [1, 2]


def test_the_directory_is_reported_new_once_and_only_when_it_did_not_exist(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    writer.append({"seq": 0}, NEXT_DAY, clock, 5.0, fresh)
    assert fresh.calls == 1
    other = FileLineWriter(str(events), "cli-2-2", threading.Lock())
    other.append({"seq": 0}, DAY, clock, 5.0, fresh)
    assert fresh.calls == 1  # the directory was there already


def test_the_file_is_opened_for_appending_and_other_writers_never_share_it(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    writer.append({"seq": 0, "who": "first"}, DAY, clock, 5.0, fresh)
    writer.close()
    again = FileLineWriter(str(events), "mcp-1-1", threading.Lock())
    again.append({"seq": 0, "who": "second"}, DAY, clock, 5.0, fresh)
    assert [e["who"] for e in lines(events / DAY / "mcp-1-1.jsonl")] == ["first", "second"]


def test_a_failure_to_open_raises_and_the_file_made_later_starts_at_one(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    events.parent.mkdir(parents=True)
    events.write_text("a file where the directory should be")
    with pytest.raises(OSError):
        writer.append({"seq": 0}, DAY, clock, 0.0, fresh)
    events.unlink()
    writer.append({"seq": 0}, DAY, clock, 0.0, fresh)
    assert [e["seq"] for e in lines(events / DAY / "mcp-1-1.jsonl")] == [1]  # a new file starts at 1


def test_after_a_failure_the_directory_is_not_tried_again_before_the_retry_window_has_passed(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    events.parent.mkdir(parents=True)
    events.write_text("blocked")
    with pytest.raises(OSError):
        writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    events.unlink()
    clock.advance(4.9)
    with pytest.raises(OSError, match="retrying later"):
        writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    assert not events.exists()  # nothing was tried
    clock.advance(0.2)
    writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    assert lines(events / DAY / "mcp-1-1.jsonl")[0]["seq"] == 1


def test_a_file_that_cannot_be_opened_is_opened_once_it_can_be(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    writer.append({"seq": 0}, DAY, clock, 0.0, fresh)
    path = events / DAY / "mcp-1-1.jsonl"
    path.unlink()
    path.mkdir()  # the file cannot be opened any more
    writer.close()
    with pytest.raises(OSError):
        writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    path.rmdir()
    clock.advance(6)
    writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    assert [e["seq"] for e in lines(path)] == [1]


def test_close_is_harmless_when_nothing_is_open_and_when_repeated(tmp_path: Path) -> None:
    writer, _, clock, fresh = make(tmp_path)
    writer.close()
    writer.append({"seq": 0}, DAY, clock, 5.0, fresh)
    writer.close()
    writer.close()


def test_threads_writing_at_once_never_interleave_or_repeat_a_number(tmp_path: Path) -> None:
    writer, events, clock, fresh = make(tmp_path)
    per_thread, workers = 200, 8

    def work() -> None:
        for i in range(per_thread):
            writer.append({"seq": 0, "pad": "p" * 100, "i": i}, DAY, clock, 5.0, fresh)

    threads = [threading.Thread(target=work) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(int(str(e["seq"])) for e in lines(events / DAY / "mcp-1-1.jsonl")) == list(range(1, per_thread * workers + 1))
