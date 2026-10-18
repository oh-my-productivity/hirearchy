"""The vocabulary of the event log format: the constants that the writer and the readers share, and how a file name is read."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from orgmcp import eventlog
from orgmcp.eventlog import DAY_RE, ENVELOPE, EVENTS_REL, LINE_MAX, PROCS, SCHEMA_VERSION, EventFile, event_file


def test_the_format_constants_are_the_ones_the_event_files_have_always_had() -> None:
    assert SCHEMA_VERSION == 1 and LINE_MAX == 8192
    assert EVENTS_REL == Path(".runtime") / "events"
    assert ENVELOPE == ("v", "ts", "seq", "proc", "pid", "kind", "actor", "run", "trace")
    assert PROCS == ("scheduler", "mcp", "cli")


@pytest.mark.parametrize("name, ok", [("2026-10-18", True), ("2026-10-1", False), ("scratch", False), ("2026-10-18x", False),
                                      ("2026-10-18\n", False), (" 2026-10-18", False), ("12026-10-18", False)])
def test_a_day_directory_is_a_date(name: str, ok: bool) -> None:
    assert bool(DAY_RE.fullmatch(name)) is ok


def test_a_file_name_says_the_process_its_pid_and_its_start() -> None:
    path = Path("/org/.runtime/events/2026-10-18/scheduler-4242-1792317600000.jsonl")
    file = event_file(path)
    assert file == EventFile(path, "2026-10-18", "scheduler", 4242, "scheduler-4242-1792317600000")
    assert file.start_ms == 1792317600000


@pytest.mark.parametrize("name", ["odd.jsonl", "mcp-x-1.jsonl", "mcp-1.jsonl", "-1-2.jsonl", "mcp-1-2-3x.jsonl"])
def test_a_name_of_another_shape_has_no_process(name: str) -> None:
    file = event_file(Path("2026-10-18") / name)
    assert (file.proc, file.pid, file.start_ms, file.day, file.stem) == ("", 0, 0, "2026-10-18", name[: -len(".jsonl")])


def test_a_process_name_may_contain_a_dash() -> None:
    file = event_file(Path("d/2026-10-18/my-proc-7-9.jsonl"))
    assert (file.proc, file.pid, file.start_ms) == ("my-proc", 7, 9)


def test_an_event_file_is_immutable_data() -> None:
    file = event_file(Path("2026-10-18/mcp-1-2.jsonl"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        file.pid = 3  # type: ignore[misc]
    assert hash(file) == hash(event_file(Path("2026-10-18/mcp-1-2.jsonl")))


def test_the_package_exports_exactly_its_api() -> None:
    assert eventlog.__all__ == eventlog.api.__all__
    assert set(eventlog.__all__) == {
        "DAY_RE", "ENVELOPE", "EVENTS_REL", "EventFile", "EventFollower", "EventFollowers", "EventReader", "LINE_MAX", "PROCS",
        "SCHEMA_VERSION", "event_file",
    }
