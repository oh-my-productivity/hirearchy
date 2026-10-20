"""Contract of ``IgnoreList`` (``.gitignore``): the real file list and the in-memory one."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.snapshots import RUNTIME_IGNORE_LINES, IgnoreList
from orgmcp.snapshots.testing import IMPLEMENTATIONS, IgnoreHarness

INITIAL = [".tmp-*", "runs/", ".kiro/", ".runtime/scheduler.pid", ".runtime/events/"]


@pytest.fixture(params=IMPLEMENTATIONS[IgnoreList], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> IgnoreHarness:
    made = cast(Callable[[Path], IgnoreHarness], request.param)(tmp_path)
    assert isinstance(made.ignore, IgnoreList)
    return made


def test_write_initial_writes_each_line_followed_by_a_newline(h: IgnoreHarness) -> None:
    h.ignore.write_initial(INITIAL)
    assert h.read() == ".tmp-*\nruns/\n.kiro/\n.runtime/scheduler.pid\n.runtime/events/\n"


def test_write_initial_replaces_what_is_there(h: IgnoreHarness) -> None:
    h.put("old\nstuff\n")
    h.ignore.write_initial(["new"])
    assert h.read() == "new\n"


def test_write_initial_of_no_lines_writes_an_empty_file(h: IgnoreHarness) -> None:
    h.ignore.write_initial([])
    assert h.read() == ""


def test_ensure_creates_the_file_when_there_is_none(h: IgnoreHarness) -> None:
    assert h.read() is None
    h.ignore.ensure(["a/", "b"])
    assert h.read() == "a/\nb\n"


def test_ensure_appends_only_the_missing_lines_after_the_existing_text(h: IgnoreHarness) -> None:
    h.put("runs/\n.kiro/\n")
    h.ignore.ensure([".kiro/", "events/", "runs/", "new"])
    assert h.read() == "runs/\n.kiro/\nevents/\nnew\n"


def test_ensure_of_lines_that_are_all_present_leaves_the_file_as_it_is(h: IgnoreHarness) -> None:
    text = "a\nb\n\n\n# comment\n"  # not even normalised
    h.put(text)
    h.ignore.ensure(["b", "a"])
    assert h.read() == text


def test_ensure_adds_the_newline_a_file_lacks_at_its_end(h: IgnoreHarness) -> None:
    h.put("a")
    h.ignore.ensure(["b"])
    assert h.read() == "a\nb\n"


def test_ensure_normalises_trailing_blank_lines_only_when_it_appends(h: IgnoreHarness) -> None:
    h.put("a\n\n\n")
    h.ignore.ensure(["b"])
    assert h.read() == "a\nb\n"


def test_ensure_adds_a_line_once_even_when_it_is_asked_for_twice(h: IgnoreHarness) -> None:
    h.ignore.ensure(["x", "x"])
    assert h.read() == "x\n"


def test_a_line_matches_as_a_whole_not_as_a_part_of_another(h: IgnoreHarness) -> None:
    h.put("events/old\n")
    h.ignore.ensure(["events/"])
    assert h.read() == "events/old\nevents/\n"


def test_ensure_runtime_files_adds_exactly_the_four_lines(h: IgnoreHarness) -> None:
    h.put(".tmp-*\nruns/\n")
    h.ignore.ensure_runtime_files()
    assert h.read() == ".tmp-*\nruns/\n" + "".join(f"{line}\n" for line in RUNTIME_IGNORE_LINES)


def test_ensure_runtime_files_adds_only_the_ones_that_are_missing(h: IgnoreHarness) -> None:
    h.put(".runtime/scheduler.log\n.runtime/events/\n")
    h.ignore.ensure_runtime_files()
    assert h.read() == ".runtime/scheduler.log\n.runtime/events/\n.runtime/running.json\n.runtime/scheduler.exit\n"


def test_ensure_runtime_files_is_idempotent(h: IgnoreHarness) -> None:
    h.ignore.write_initial(INITIAL)
    h.ignore.ensure_runtime_files()
    once = h.read()
    h.ignore.ensure_runtime_files()
    assert h.read() == once


def test_a_new_organization_ends_up_ignoring_events_once(h: IgnoreHarness) -> None:
    h.ignore.write_initial(INITIAL)
    h.ignore.ensure_runtime_files()
    assert (h.read() or "").split().count(".runtime/events/") == 1


def test_ensure_does_not_raise_when_the_file_cannot_be_used(h: IgnoreHarness) -> None:
    h.break_storage()
    h.ignore.ensure(["a"])
    h.ignore.ensure_runtime_files()


def test_ensure_does_nothing_when_the_organization_directory_is_gone(h: IgnoreHarness) -> None:
    h.remove_directory()
    h.ignore.ensure(["a"])
    h.ignore.ensure_runtime_files()
    assert h.read() is None


def test_write_initial_reports_a_file_it_cannot_write(h: IgnoreHarness) -> None:
    h.break_storage()
    with pytest.raises(OSError):
        h.ignore.write_initial(["a"])
