"""The composition root builds the reviewer of every organization from the ports below it."""

from __future__ import annotations

from typing import Any

from orgmcp.review import HealthReviewer
from orgmcp.review._reviewer import LedgerHealthReviewer


def test_the_runtime_builds_the_real_class(scenario: Any) -> None:
    reviewer = scenario.runtime.health_reviewer
    assert isinstance(reviewer, LedgerHealthReviewer) and isinstance(reviewer, HealthReviewer)


def test_the_reviewer_is_built_once_per_organization(scenario: Any) -> None:
    runtime = scenario.runtime
    assert runtime.health_reviewer is runtime.health_reviewer


def test_the_reviewer_reads_the_run_logs_and_the_retired_trees_of_the_organization(scenario: Any) -> None:
    (scenario.dir("ceo") / "runs" / "20260101T000000000001.log").touch()
    retired = scenario.root / ".retired" / "gone-S" / "runs"
    retired.mkdir(parents=True)
    (retired / "20260101T000000000002.log").touch()
    assert scenario.runtime.health_reviewer.total_runs() == 2

