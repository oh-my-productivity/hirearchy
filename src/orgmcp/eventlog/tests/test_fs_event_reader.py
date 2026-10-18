"""``FsEventReader``: what only the disk implementation does (the shared behaviour is in ``test_contract_event_reader``)."""

from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest

from orgmcp.eventlog import EventReader, event_file
from orgmcp.eventlog import _reader
from orgmcp.eventlog._reader import FsEventReader
from orgmcp.eventlog.testing import EventLogHarness, fs_event_log
from orgmcp.kernel import OrgPaths

from ._support import at, day

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-eventlog")


@pytest.fixture
def h(tmp_path: Path) -> EventLogHarness:
    return fs_event_log(tmp_path)


def test_it_is_an_event_reader_over_the_events_directory_of_its_layout(tmp_path: Path) -> None:
    org = tmp_path / "org"
    reader = FsEventReader(OrgPaths(org))
    assert isinstance(reader, EventReader) and reader.files() == []
    target = org / ".runtime" / "events" / day(0)
    target.mkdir(parents=True)
    (target / "mcp-1-2.jsonl").write_text(json.dumps({"ts": at(1).isoformat(), "kind": "k"}) + "\n")
    assert [f.path for f in reader.files()] == [target / "mcp-1-2.jsonl"]
    assert [ev["kind"] for ev in reader.events()] == ["k"]


def test_an_events_directory_that_is_a_file_has_no_files(tmp_path: Path) -> None:
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime" / "events").write_text("in the way")
    assert FsEventReader(OrgPaths(tmp_path)).files() == []


def test_a_file_named_like_a_day_is_not_a_day_directory(h: EventLogHarness, tmp_path: Path) -> None:
    (tmp_path / ".runtime" / "events").mkdir(parents=True)
    (tmp_path / ".runtime" / "events" / day(0)).write_text("a file, not a directory")
    assert h.reader.files() == []


def test_a_path_that_cannot_be_opened_as_a_file_has_no_events(h: EventLogHarness, tmp_path: Path) -> None:
    in_the_way = tmp_path / ".runtime" / "events" / day(0) / "mcp-9-9.jsonl"
    in_the_way.mkdir(parents=True)  # a directory with an event file's name
    file = event_file(in_the_way)
    assert list(h.reader.read_file(file)) == [] and h.reader.tail(file) == [] and h.reader.head(file) is None


def test_timed_looks_at_the_disk_when_it_is_first_iterated(h: EventLogHarness) -> None:
    stream = h.reader.timed()
    a = h.log.emit(at(1))
    assert [ev for _, ev in stream] == [a]


def test_a_file_that_vanishes_after_it_was_listed_has_no_events(h: EventLogHarness) -> None:
    h.log.emit(at(1))
    (file,) = h.reader.files()
    file.path.unlink()
    assert list(h.reader.read_file(file)) == [] and h.reader.tail(file) == [] and h.reader.head(file) is None


def test_a_file_that_vanishes_during_the_listing_of_a_window_is_dropped(h: EventLogHarness, monkeypatch: pytest.MonkeyPatch) -> None:
    h.log.emit(at(1), proc="mcp", pid=1)
    h.log.emit(at(2), proc="mcp", pid=2)
    gone = h.reader.files()[0].path
    real_stat = Path.stat

    def stat(self: Path, *args: object, **kwargs: object) -> object:
        if self == gone:
            raise FileNotFoundError(str(self))
        return real_stat(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "stat", stat)
    assert [f.pid for f in h.reader.files(since=at(0))] == [2]


def test_files_outside_the_day_window_are_never_opened(h: EventLogHarness, monkeypatch: pytest.MonkeyPatch) -> None:
    h.log.emit(at(-86400 * 3), proc="mcp", pid=1)
    h.log.emit(at(0), proc="mcp", pid=2)
    opened: list[str] = []
    real_open = builtins.open

    def spy(file: object, *args: object, **kwargs: object) -> object:
        opened.append(str(file))
        return real_open(file, *args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(_reader, "open", spy, raising=False)
    assert len(list(h.reader.events(at(-3600), at(3600)))) == 1
    assert len(opened) == 1 and day(0) in opened[0]


def test_the_head_and_the_tail_read_one_file_and_not_the_others(h: EventLogHarness) -> None:
    a = h.log.emit(at(1), "start", proc="scheduler", pid=1)
    h.log.emit(at(2), "other", proc="mcp", pid=2)
    scheduler = next(f for f in h.reader.files() if f.proc == "scheduler")
    assert h.reader.head(scheduler) == a and h.reader.tail(scheduler) == [a]


def test_a_file_given_by_path_alone_can_be_read(h: EventLogHarness) -> None:
    a = h.log.emit(at(1))
    (listed,) = h.reader.files()
    assert h.reader.tail(event_file(listed.path)) == [a]
