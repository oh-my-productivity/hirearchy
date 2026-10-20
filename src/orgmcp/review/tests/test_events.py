# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
import shutil

import pytest
from testkit import telemetry_world as telemetry
from testkit.legacy.orgmcp.core import ROOT


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    telemetry.reset()
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def read_events(org, kind=None):
    """Every event of the org, merged by time (the way a reader would)."""
    out = []
    for f in event_files(org):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))  # every line is a valid JSON object
    out.sort(key=lambda e: (e["ts"], e["seq"]))
    return [e for e in out if kind is None or e["kind"] == kind]


def test_review_run_event(org):
    from testkit import review_world as review

    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    result = review.review(org)
    (ev,) = read_events(org, "review.run")
    assert ev["flagged"] == result.flagged and ev["notes"] == [n.to for n in result.notes]
    review.review(org, dry_run=True)
    assert len(read_events(org, "review.run")) == 1  # a dry run changes nothing and says nothing
