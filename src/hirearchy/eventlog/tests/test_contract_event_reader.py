"""Contract of ``EventReader``: the event files of the disk and of the in-memory log are listed and read alike."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from hirearchy.eventlog import EventFile, EventReader
from hirearchy.eventlog.testing import IMPLEMENTATIONS, EventLogHarness

from ._support import at, day, where


@pytest.fixture(params=IMPLEMENTATIONS[EventReader], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> EventLogHarness:
    made = cast(EventLogHarness, request.param(tmp_path))
    assert isinstance(made.reader, EventReader)
    return made


# ------------------------------------------------------------------------------------------------------------------- files


def test_an_organization_without_events_has_no_files_and_no_events(h: EventLogHarness) -> None:
    assert h.reader.files() == [] and list(h.reader.timed()) == [] and list(h.reader.events()) == []


def test_files_are_listed_by_day_then_by_name_and_say_what_they_are(h: EventLogHarness) -> None:
    h.log.emit(at(10), proc="mcp", pid=1)
    h.log.emit(at(5), proc="scheduler", pid=2)
    h.log.emit(at(-86400 * 3), proc="cli", pid=3)
    files = h.reader.files()
    assert where(files) == [(day(-3), "cli", 3), (day(0), "mcp", 1), (day(0), "scheduler", 2)]
    first = files[1]
    assert first.stem == h.log.file(day(0), "mcp", 1).stem
    assert first.path.name == first.stem + ".jsonl" and first.path.parent.name == first.day
    assert first.start_ms == int(at(0).timestamp() * 1000)  # the first process the harness named


def test_only_event_files_are_listed(h: EventLogHarness) -> None:
    h.log.emit(at(10), proc="mcp", pid=1)
    h.log.foreign(day(0), "notes.txt", b"not an event file")
    h.log.foreign(day(0), ".mcp-1-2.jsonl", b'{"ts": "2026-10-18T10:00:00+00:00"}\n')  # hidden
    h.log.foreign("scratch", "mcp-1-2.jsonl", b'{"ts": "2026-10-18T10:00:00+00:00"}\n')  # not a day directory
    h.log.foreign("2026-10-1", "mcp-1-2.jsonl", b"")  # not a day directory either
    assert where(h.reader.files()) == [(day(0), "mcp", 1)]


def test_a_name_of_another_shape_is_still_an_event_file_without_a_process(h: EventLogHarness) -> None:
    h.log.foreign(day(0), "odd.jsonl", b"")
    (only,) = h.reader.files()
    assert (only.day, only.proc, only.pid, only.stem, only.start_ms) == (day(0), "", 0, "odd", 0)


def test_the_time_window_selects_day_directories(h: EventLogHarness) -> None:
    for d in (-3, 0, 2):
        h.log.emit(at(86400 * d), proc="mcp", pid=1)
    assert [f.day for f in h.reader.files()] == [day(-3), day(0), day(2)]
    assert [f.day for f in h.reader.files(at(-3600), at(3600))] == [day(0)]
    assert [f.day for f in h.reader.files(at(-3600))] == [day(0), day(2)]
    assert [f.day for f in h.reader.files(until=at(3600))] == [day(-3), day(0)]
    assert [f.day for f in h.reader.files(at(86400), at(86400 * 3))] == [day(2)]


def test_the_days_of_a_window_are_utc_days(h: EventLogHarness) -> None:
    h.log.emit(at(13 * 3600), proc="mcp", pid=1)  # 2026-10-18 23:00Z
    plus_two = timezone(timedelta(hours=2))
    assert [f.day for f in h.reader.files(datetime(2026, 10, 19, 0, 30, tzinfo=plus_two))] == [day(0)]  # 2026-10-18 22:30Z
    assert h.reader.files(datetime(2026, 10, 19, 2, 30, tzinfo=plus_two)) == []  # 2026-10-19 00:30Z
    assert [f.day for f in h.reader.files(until=datetime(2026, 10, 18, 1, 0, tzinfo=plus_two))] == []  # 2026-10-17 23:00Z


def test_a_file_not_written_since_the_start_of_the_window_is_skipped(h: EventLogHarness) -> None:
    h.log.emit(at(10), proc="mcp", pid=1)
    h.log.emit(at(5000), proc="scheduler", pid=2)
    assert where(h.reader.files(at(60))) == [(day(0), "scheduler", 2)]
    assert where(h.reader.files(at(10))) == [(day(0), "mcp", 1), (day(0), "scheduler", 2)]  # written exactly then: kept
    old = h.log.file(day(0), "mcp", 1)
    h.log.touch(old, at(7000))
    assert where(h.reader.files(at(6000))) == [(day(0), "mcp", 1)]


def test_the_end_of_the_window_does_not_skip_a_file_that_was_written_later(h: EventLogHarness) -> None:
    h.log.emit(at(10), proc="mcp", pid=1)
    h.log.touch(h.log.file(day(0), "mcp", 1), at(9000))  # written long after ``until``: it can still hold earlier events
    assert where(h.reader.files(until=at(60))) == [(day(0), "mcp", 1)]


# ------------------------------------------------------------------------------------------------------------------ read_file


def test_read_file_yields_time_and_event_in_file_order_and_keeps_unknown_fields(h: EventLogHarness) -> None:
    a = h.log.emit(at(2), "kind.from.the.future", whatever={"x": [1, 2]}, brand_new_field=1)
    b = h.log.emit(at(1), "run.start", agent="ceo")  # written second, earlier time: file order, not time order
    (file,) = h.reader.files()
    assert list(h.reader.read_file(file)) == [(at(2), a), (at(1), b)]


def test_read_file_tolerates_a_partial_last_line(h: EventLogHarness) -> None:
    a = h.log.emit(at(1))
    h.log.raw(day(0), "mcp", 4242, '{"v": 1, "ts": "2026-10-18T10:0')
    (file,) = h.reader.files()
    assert [ev for _, ev in h.reader.read_file(file)] == [a]


def test_read_file_skips_lines_that_are_not_events(h: EventLogHarness) -> None:
    a = h.log.emit(at(1))
    for text in (
        "not json\n",
        "[1, 2]\n",
        '"a string"\n',
        "7\n",
        "null\n",
        "\n",
        "   \n",
        '{"kind": "no ts"}\n',
        '{"ts": "garbage"}\n',
        '{"ts": null}\n',
        '{"ts": 17}\n',
    ):
        h.log.raw(day(0), "mcp", 4242, text)
    h.log.foreign(day(0), h.log.file(day(0), "mcp", 4242).path.name, b"\xfd\xfe not utf-8\n")
    b = h.log.emit(at(2))
    (file,) = h.reader.files()
    assert [ev for _, ev in h.reader.read_file(file)] == [a, b]


def test_a_time_without_a_zone_is_utc(h: EventLogHarness) -> None:
    h.log.raw(day(0), "mcp", 1, '{"ts": "2026-10-18T10:00:05", "kind": "k"}\n')
    h.log.raw(day(0), "mcp", 1, '{"ts": "2026-10-18T12:00:05+02:00", "kind": "k"}\n')
    (file,) = h.reader.files()
    times = [t for t, _ in h.reader.read_file(file)]
    assert times == [at(5), at(5)] and all(t.tzinfo is not None for t in times)


def test_a_file_that_does_not_exist_has_no_events(h: EventLogHarness) -> None:
    ghost = h.log.file(day(0), "mcp", 99)
    assert list(h.reader.read_file(ghost)) == [] and h.reader.tail(ghost) == [] and h.reader.head(ghost) is None


# --------------------------------------------------------------------------------------------------------------- timed, events


def test_events_are_merged_over_the_files_by_time(h: EventLogHarness) -> None:
    got = [
        h.log.emit(at(10), "tool.call", proc="mcp", pid=1),
        h.log.emit(at(5), "run.start", proc="scheduler", pid=2),
        h.log.emit(at(20), "tool.call", proc="mcp", pid=1),
        h.log.emit(at(15), "scheduler.heartbeat", proc="scheduler", pid=2),
        h.log.emit(at(12), "kind.from.the.future", proc="cli", pid=3),
        h.log.emit(at(86400 + 1), "tool.call", proc="mcp", pid=1),  # the next day's file
    ]
    h.log.raw(day(0), "mcp", 1, '{"v": 1, "ts": "2026-10-18T10:0')
    want = sorted(got, key=lambda ev: str(ev["ts"]))
    assert [ev for _, ev in h.reader.timed()] == want
    assert [t for t, _ in h.reader.timed()] == sorted(t for t, _ in h.reader.timed())
    assert list(h.reader.events()) == want


def test_events_with_the_same_time_keep_the_order_of_the_files(h: EventLogHarness) -> None:
    a = h.log.emit(at(5), "tool.call", proc="mcp", pid=1)
    b = h.log.emit(at(5), "run.start", proc="scheduler", pid=2)
    c = h.log.emit(at(5), "tool.call", proc="cli", pid=3)
    assert list(h.reader.events()) == [c, a, b]  # cli-3 < mcp-1 < scheduler-2 by file name


def test_the_window_is_inclusive_and_cuts_inside_a_file(h: EventLogHarness) -> None:
    evs = {s: h.log.emit(at(s), "tool.call", n=s) for s in (0, 10, 20, 30, 40)}
    assert list(h.reader.events(at(10), at(30))) == [evs[10], evs[20], evs[30]]
    assert list(h.reader.events(since=at(25))) == [evs[30], evs[40]]
    assert list(h.reader.events(until=at(5))) == [evs[0]]
    assert list(h.reader.events(at(11), at(19))) == []
    assert [t for t, _ in h.reader.timed(at(10), at(20))] == [at(10), at(20)]


def test_the_day_window_is_a_property_of_the_directory_not_of_the_modification_time(h: EventLogHarness) -> None:
    h.log.emit(at(-86400 * 3), "tool.call", tool="old")
    h.log.emit(at(0), "tool.call", tool="today")
    h.log.emit(at(86400 * 2), "tool.call", tool="later")
    h.log.touch(h.log.file(day(-3), "mcp", 4242), at(0))  # the old file was written just now: its events are still 3 days old
    assert [ev["tool"] for ev in h.reader.events(at(-3600), at(3600))] == ["today"]
    assert [ev["tool"] for ev in h.reader.events(at(-86400 * 4))] == ["old", "today", "later"]


# ---------------------------------------------------------------------------------------------------------------- tail, head


def test_tail_is_the_complete_events_at_the_end_of_a_file(h: EventLogHarness) -> None:
    evs = [h.log.emit(at(s), "tool.call", n=s) for s in range(1, 21)]
    (file,) = h.reader.files()
    assert h.reader.tail(file) == evs  # the default window holds the whole small file


def test_tail_drops_the_line_that_the_cut_makes_partial(h: EventLogHarness) -> None:
    evs = [h.log.emit(at(s), "tool.call", n=s) for s in range(1, 21)]
    (file,) = h.reader.files()
    sizes = [len(json.dumps(ev)) + 1 for ev in evs]
    window = sizes[-1] + sizes[-2] + sizes[-3] // 2  # ends in the middle of the third line from the end
    assert h.reader.tail(file, window) == evs[-2:]
    assert h.reader.tail(file, sum(sizes)) == evs  # exactly the size of the file: nothing is cut
    assert h.reader.tail(file, sum(sizes) + 1000) == evs


def test_tail_skips_a_partial_last_line(h: EventLogHarness) -> None:
    evs = [h.log.emit(at(s)) for s in (1, 2)]
    h.log.raw(day(0), "mcp", 4242, '{"v": 1, "ts": "2026-10-18T10:0')
    (file,) = h.reader.files()
    assert h.reader.tail(file) == evs


def test_tail_skips_lines_that_are_not_objects_and_keeps_events_without_a_time(h: EventLogHarness) -> None:
    h.log.raw(day(0), "mcp", 1, 'garbage\n[1]\n{"kind": "no ts"}\n')
    a = h.log.emit(at(1), proc="mcp", pid=1)
    (file,) = h.reader.files()
    assert h.reader.tail(file) == [{"kind": "no ts"}, a]  # unlike read_file, tail does not look at ts


def test_head_is_the_first_line_of_the_file(h: EventLogHarness) -> None:
    a = h.log.emit(at(1), "scheduler.start", mode="work")
    h.log.emit(at(2), "scheduler.heartbeat")
    (file,) = h.reader.files()
    assert h.reader.head(file) == a


@pytest.mark.parametrize("first", ["garbage\n", "[1, 2]\n", '{"v": 1, "ts": "2026-10-18T10:0', "\n", "7\n"])
def test_head_is_none_when_the_file_starts_with_something_else(h: EventLogHarness, first: str) -> None:
    file = h.log.raw(day(0), "mcp", 1, first)
    h.log.emit(at(1), proc="mcp", pid=1)
    assert h.reader.head(file) is None


def test_head_does_not_look_at_the_time(h: EventLogHarness) -> None:
    file = h.log.raw(day(0), "mcp", 1, '{"kind": "no ts"}\n')
    assert h.reader.head(file) == {"kind": "no ts"}


def test_head_of_an_empty_file_is_none(h: EventLogHarness) -> None:
    h.log.foreign(day(0), "mcp-1-2.jsonl", b"")
    (file,) = h.reader.files()
    assert isinstance(file, EventFile) and h.reader.head(file) is None and h.reader.tail(file) == []
