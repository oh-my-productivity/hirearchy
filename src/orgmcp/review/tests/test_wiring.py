"""The composition root builds the reviewer of every organization from the ports below it."""

from __future__ import annotations

from typing import Any

import pytest

from orgmcp.review import HealthReviewer
from orgmcp.review._reviewer import LedgerHealthReviewer
from orgmcp.templates.testing import RecordingNotices

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-review")


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


def test_the_notes_are_worded_by_the_notices_of_the_runtime(scenario: Any) -> None:
    from dataclasses import replace

    notices = RecordingNotices()
    scenario.runtime = replace(scenario.runtime, notices=notices)  # tests replace the ports of a runtime under the reviewer
    reviewer = scenario.runtime.health_reviewer
    reviewer.review(dry_run=True)
    assert any(name == "review_root" for name, _ in notices.calls)
