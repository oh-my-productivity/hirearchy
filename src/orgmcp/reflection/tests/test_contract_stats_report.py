"""Contract of ``StatsReport``: the counts of a set of cases print themselves. ``Stats`` is its one implementation (data)."""

from __future__ import annotations

import pytest

from orgmcp.reflection import Stats, StatsReport

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-reflection")


def test_the_counts_are_a_stats_report() -> None:
    assert isinstance(Stats(), StatsReport)


def test_nothing_counted_says_so_without_an_average_or_feedback() -> None:
    assert Stats().line() == "0 request(s): 0 done, 0 failed, 0 open; 0 reworked; no feedback"


def test_the_finished_cases_are_the_done_and_the_failed() -> None:
    assert Stats(requests=5, done=2, failed=1, open=2).finished == 3 and Stats().finished == 0


def test_the_average_is_runs_per_finished_case_to_one_decimal() -> None:
    assert Stats(done=2, failed=1, finished_runs=10).avg_runs == 3.3 and Stats(done=1, finished_runs=4).avg_runs == 4.0
    assert Stats(open=2, finished_runs=0).avg_runs is None


def test_the_line_gives_the_average_without_trailing_zeros() -> None:
    assert Stats(requests=1, done=1, finished_runs=4).line() == "1 request(s): 1 done, 0 failed, 0 open; 0 reworked; avg 4 runs; no feedback"
    assert "avg 3.3 runs" in Stats(requests=3, done=2, failed=1, finished_runs=10).line()


def test_the_line_counts_the_feedback() -> None:
    assert Stats(requests=2, done=2, accept=1, reject=1).line().endswith("; feedback 1 accept, 1 reject")


def test_the_line_says_how_many_accepts_came_after_a_reject() -> None:
    assert Stats(requests=3, done=3, accept=2, reject=1, accept_after_reject=1).line().endswith("; feedback 2 accept (1 after a reject), 1 reject")
    assert "after a reject" not in Stats(requests=1, done=1, accept=1).line()
