"""The runs slice of the ``Org`` facade: ``runs_used`` and ``start_run_log`` behave as they always did, and now go through the runtime's ports."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org, wiring
from orgmcp.kernel import Clock
from orgmcp.runs.testing import MemoryRuns
from testkit.clocks import ClockReading


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


def stamp(org: Org, addr: str, text: str) -> Path:
    runs = org.dir(addr) / "runs"
    runs.mkdir(exist_ok=True)
    (runs / text).write_text("x", encoding="utf-8")
    return runs / text


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_runs_used_counts_the_visible_logs(org: Org) -> None:
    assert org.runs_used("ceo") == 0
    stamp(org, "ceo", "20261018T100000000001.log")
    stamp(org, "ceo", "20261018T100000000002.log")
    stamp(org, "ceo", ".hidden.log")
    stamp(org, "ceo", "notes.txt")
    assert org.runs_used("ceo") == 2 and org.runs_used("ceo/eng") == 0 and org.runs_used("root") == 0


def test_runs_used_of_an_address_that_is_spelled_differently(org: Org) -> None:
    stamp(org, "ceo/eng", "20261018T100000000001.log")
    assert org.runs_used(" /ceo/eng/ ") == 1


def test_start_run_log_creates_the_empty_log_and_consumes_a_run(org: Org) -> None:
    org.delegate("root", "ceo", "T", "g", "a", budget=5)
    org.runtime = wiring.open_runtime(org.root, {Clock: ClockReading(lambda: datetime(2031, 5, 6, 7, 8, 9, 123456, tzinfo=timezone.utc))})
    before = org.budget("ceo")
    assert before is not None
    log = org.start_run_log("ceo")
    assert log == org.root / "ceo" / "runs" / "20310506T070809123456.log" and log.read_bytes() == b""
    assert org.runs_used("ceo") == 1 and org.budget("ceo") == before - 1


def test_start_run_log_for_the_root_and_for_a_nested_agent(org: Org) -> None:
    assert org.start_run_log("root").parent == org.root / "runs"
    assert org.start_run_log("ceo/eng").parent == org.root / "ceo" / "eng" / "runs"


def test_start_run_log_makes_only_the_runs_directory(org: Org) -> None:
    org.start_run_log("ceo")
    assert (org.root / "ceo" / "runs").is_dir()
    with pytest.raises(FileNotFoundError):
        org.start_run_log("ghost")
    assert not (org.root / "ghost").exists()


def test_two_logs_in_the_same_instant_are_one_run(org: Org) -> None:
    org.runtime = wiring.open_runtime(org.root, {Clock: ClockReading(lambda: datetime(2031, 5, 6, 7, 8, 9, 123456, tzinfo=timezone.utc))})
    assert org.start_run_log("ceo") == org.start_run_log("ceo") and org.runs_used("ceo") == 1


# -------------------------------------------------------------------------------------------- through the ports (red until wired)


def test_runs_used_comes_from_the_log_reader_of_the_runtime(org: Org) -> None:
    fake = MemoryRuns(root=org.root)
    fake.add_agent("ceo")
    fake.create("ceo")
    fake.create("ceo")
    use(org, run_log_reader=fake)
    assert org.runs_used("ceo") == 2 and list((org.root / "ceo" / "runs").glob("*.log")) == []  # none on disk: the fake answered


def test_start_run_log_comes_from_the_log_writer_of_the_runtime(org: Org) -> None:
    fake = MemoryRuns(root=org.root)
    fake.add_agent("ceo")
    use(org, run_log_writer=fake)
    log = org.start_run_log("ceo")
    assert fake.count("ceo") == 1 and fake.read_log(log) == b"" and not log.exists()
