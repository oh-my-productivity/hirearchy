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


def test_service_events(org):
    brief = dict(description="A brief.", acceptance=["Short"], deliverable={"description": "one file"}, budget=4)
    org.define_service(ROOT, "ceo", "weekly", **brief)
    org.define_service(ROOT, "ceo", "weekly", add_acceptance=["Sourced"])
    org.revise_playbook("ceo", "weekly", "1. Do the thing.", "first version")
    org.retire_service(ROOT, "ceo", "weekly", "not needed")
    kinds = [e["kind"] for e in read_events(org) if e["kind"].startswith("service.")]
    assert kinds == ["service.define", "service.define", "service.revise", "service.retire"]
    first, second = read_events(org, "service.define")
    assert (first["owner"], first["service"], first["version"], first["by"], first["amendment"]) == ("ceo", "weekly", 1, "root", False)
    assert second["version"] == 2 and second["amendment"] is True
    (rev,) = read_events(org, "service.revise")
    assert rev["version"] == 1 and rev["by"] == "ceo" and rev["owner"] == "ceo"
