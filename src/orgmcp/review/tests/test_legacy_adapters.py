"""The old module-level functions are thin adapters over the reviewer of the organization they are given (``_legacy``)."""

from __future__ import annotations

import importlib
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import pytest

from orgmcp.review import Note, Review
from orgmcp.review.testing import ScriptedHealthReviewer

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-review")

review = importlib.import_module("orgmcp.review")
AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
DONE = Review(at=AT, runs=3, flagged=1, notes=[Note("root", "t", "b")])


@pytest.fixture
def fake(scenario: Any) -> ScriptedHealthReviewer:
    scripted = ScriptedHealthReviewer(DONE, due=DONE, runs=11, ledger={"at": "x", "runs": 1, "notified": {}})
    scenario.runtime = replace(scenario.runtime, health_reviewer=scripted)
    return scripted


def test_review_asks_the_reviewer_of_the_organization(scenario: Any, fake: ScriptedHealthReviewer) -> None:
    assert review.review(scenario, AT, dry_run=True) is DONE and review.review(scenario) is DONE
    assert fake.calls == [("review", AT, True), ("review", None, False)]


def test_review_if_due_total_runs_and_read_ledger_ask_it_too(scenario: Any, fake: ScriptedHealthReviewer) -> None:
    assert review.review_if_due(scenario, AT) is DONE and review.total_runs(scenario) == 11 and review.read_ledger(scenario) == {"at": "x", "runs": 1, "notified": {}}
    assert [c[0] for c in fake.calls] == ["review_if_due", "total_runs", "read_ledger"]
