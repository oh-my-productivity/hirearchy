"""Contract of ``RunLogWriter``: the filesystem writer and the in-memory fake create and extend logs the same way."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import ROOT, stamp_of
from hirearchy.runs import RunLogWriter
from hirearchy.runs.testing import IMPLEMENTATIONS, RunsHarness


@pytest.fixture(params=IMPLEMENTATIONS[RunLogWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RunsHarness:
    made = cast(Callable[[Path], RunsHarness], request.param)(tmp_path)
    assert isinstance(made.writer, RunLogWriter)
    return made


def rel(h: RunsHarness, path: Path) -> str:
    return str(path.relative_to(h.root))


def test_create_makes_an_empty_log_in_the_runs_directory_of_the_agent(h: RunsHarness) -> None:
    h.add_agent("ceo")
    path = h.writer.create("ceo")
    assert path.parent == h.root / "ceo" / "runs" and path.suffix == ".log"
    assert h.read_log(path) == b""


def test_the_name_is_the_utc_microsecond_stamp_of_the_clock(h: RunsHarness) -> None:
    h.add_agent("ceo")
    h.clock.advance(1.5)
    expected = h.clock.t + timedelta(microseconds=1)  # the fake clock moves one microsecond per reading
    path = h.writer.create("ceo")
    assert path.stem == f"{expected:%Y%m%dT%H%M%S%f}" and stamp_of(path.stem) == expected


def test_every_log_has_its_own_name_and_names_sort_in_creation_order(h: RunsHarness) -> None:
    h.add_agent("ceo")
    paths = [h.writer.create("ceo") for _ in range(4)]
    assert len({p.name for p in paths}) == 4
    assert [p.name for p in paths] == sorted(p.name for p in paths)


def test_the_existence_of_a_log_is_what_consumes_a_run(h: RunsHarness) -> None:
    h.add_agent("ceo")
    assert h.reader.count("ceo") == 0
    h.writer.create("ceo")
    assert h.reader.count("ceo") == 1
    h.writer.create("ceo")
    assert h.reader.count("ceo") == 2
    assert h.reader.count("ceo/other") == 0


def test_the_root_keeps_its_logs_in_the_organization_directory(h: RunsHarness) -> None:
    assert h.writer.create(ROOT).parent == h.root / "runs"


def test_an_agent_below_another_has_its_logs_in_its_own_directory(h: RunsHarness) -> None:
    h.add_agent("ceo/eng")
    assert h.writer.create("ceo/eng").parent == h.root / "ceo" / "eng" / "runs"


def test_an_address_is_normalised_like_everywhere(h: RunsHarness) -> None:
    h.add_agent("ceo")
    assert h.writer.create(" /ceo/ ").parent == h.root / "ceo" / "runs"


def test_an_agent_without_a_directory_cannot_have_a_log(h: RunsHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.writer.create("ghost")
    assert h.reader.count("ghost") == 0


def test_append_note_adds_a_comment_on_a_line_of_its_own(h: RunsHarness) -> None:
    path = h.put_log("ceo", "20261018T100000000001.log", "# run of ceo\nsome output")
    h.writer.append_note(rel(h, path), "killed: orphaned run of a scheduler that died")
    assert h.read_log(path) == b"# run of ceo\nsome output\n# killed: orphaned run of a scheduler that died\n"


def test_notes_follow_each_other(h: RunsHarness) -> None:
    path = h.put_log("ceo", "20261018T100000000001.log", "out\n")
    h.writer.append_note(rel(h, path), "one")
    h.writer.append_note(rel(h, path), "two")
    assert h.read_log(path) == b"out\n\n# one\n\n# two\n"


def test_a_note_for_a_log_that_is_not_there_is_silently_dropped(h: RunsHarness) -> None:
    h.add_agent("ceo")
    h.writer.append_note("ceo/runs/20261018T100000000001.log", "killed: orphaned")
    assert h.reader.count("ceo") == 0 and h.read_log(h.root / "ceo" / "runs" / "20261018T100000000001.log") is None


def test_a_note_is_not_appended_to_a_hidden_or_other_file_that_does_not_exist(h: RunsHarness) -> None:
    h.add_agent("ceo")
    h.writer.append_note("ceo/runs/.x.log", "x")
    h.writer.append_note("nowhere/at/all.log", "x")
    assert h.reader.count("ceo") == 0


def test_a_note_that_names_a_kill_is_seen_by_the_reader(h: RunsHarness) -> None:
    path = h.put_log("ceo", "20261018T100000000001.log", "# run of ceo\n")
    h.writer.append_note(rel(h, path), "killed: orphaned run of a scheduler that died")
    assert h.reader.facts(path) == {"killed": True}
