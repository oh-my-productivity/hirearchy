# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json
import shutil

import pytest
from testkit.legacy.orgmcp import telemetry
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


# --------------------------------------------------------------------------- org operations: hire, pause, ...
def test_hire_retire_pause_resume_events(org):
    org.hire("ceo", "qa", "Tester", "Test things.", model="m1")
    (hire,) = [e for e in read_events(org, "agent.hire") if e["agent"] == "ceo/qa"]
    assert hire["by"] == "ceo" and hire["actor"] == "ceo" and hire["role"] == "Tester"
    assert hire["model"] == "m1" and hire["tools"] == []
    org.pause("ceo/qa", "failures")
    org.resume("ceo/qa", "manual")
    pause, resume = read_events(org, "agent.pause")[-1], read_events(org, "agent.resume")[-1]
    assert pause["agent"] == "ceo/qa" and pause["reason"] == "failures"
    assert resume["agent"] == "ceo/qa" and resume["reason"] == "manual" and resume["previous"] == "failures"
    org.resume("ceo/qa")  # not paused: nothing to record
    assert len(read_events(org, "agent.resume")) == 1
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.retire(ROOT, "ceo/eng", "no longer needed")
    (ret,) = read_events(org, "agent.retire")
    assert ret["agent"] == "ceo/eng" and ret["by"] == "root" and ret["reason"] == "no longer needed"
    assert ret["returned_budget"] == 0
