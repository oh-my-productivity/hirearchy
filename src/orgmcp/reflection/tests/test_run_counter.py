"""``LogRunCounter``: the runs of a team between two moments are the run logs whose name falls in the window."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.reflection._ports import RunCounter
from orgmcp.reflection._runs import LogRunCounter
from orgmcp.runs.testing import RunsHarness, fs_runs, memory_runs

RED = pytest.mark.xfail(strict=True, reason="red: C-reflection")

A, B, C, D = "20260101T000001000000", "20260101T000002000000", "20260101T000003000000", "20260101T000004000000"


@pytest.fixture(params=[fs_runs, memory_runs], ids=lambda f: f.__name__)
def runs(request: pytest.FixtureRequest, tmp_path: Path) -> RunsHarness:
    harness: RunsHarness = request.param(tmp_path)
    for addr in ("ceo", "ceo/eng", "ops"):
        harness.add_agent(addr)
    return harness


def log(runs: RunsHarness, addr: str, stamp: str, suffix: str = ".log") -> None:
    runs.put_log(addr, stamp + suffix, "# run\n")


def test_it_is_a_run_counter(runs: RunsHarness) -> None:
    assert isinstance(LogRunCounter(runs.reader), RunCounter)


@RED
def test_the_logs_of_every_agent_of_the_team_in_the_window_are_counted(runs: RunsHarness) -> None:
    for addr, stamp in (("ceo", B), ("ceo/eng", C), ("ops", C)):
        log(runs, addr, stamp)
    assert LogRunCounter(runs.reader).runs_between(["ceo", "ceo/eng"], A, D) == 2


@RED
def test_a_window_without_an_end_runs_to_now(runs: RunsHarness) -> None:
    for stamp in (A, B, C):
        log(runs, "ceo", stamp)
    assert LogRunCounter(runs.reader).runs_between(["ceo"], B, None) == 2


@RED
def test_the_window_edges_are_compared_on_the_first_21_characters(runs: RunsHarness) -> None:
    for stamp in (A, B, C):
        log(runs, "ceo", stamp)
    counter = LogRunCounter(runs.reader)
    assert counter.runs_between(["ceo"], B, B) == 1 and counter.runs_between(["ceo"], A, C) == 3 and counter.runs_between(["ceo"], C, A) == 0


@RED
def test_hidden_logs_and_other_files_are_not_runs(runs: RunsHarness) -> None:
    log(runs, "ceo", B)
    log(runs, "ceo", "." + B)
    log(runs, "ceo", B, ".txt")
    assert LogRunCounter(runs.reader).runs_between(["ceo"], A, D) == 1


@RED
def test_an_agent_without_logs_adds_none(runs: RunsHarness) -> None:
    assert LogRunCounter(runs.reader).runs_between(["ceo", "ghost"], A, None) == 0


@RED
def test_nobody_in_the_team_made_no_runs(runs: RunsHarness) -> None:
    log(runs, "ceo", B)
    assert LogRunCounter(runs.reader).runs_between([], A, None) == 0
