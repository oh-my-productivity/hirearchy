# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
import shutil

import pytest
from testkit.reach.hirearchy.core import ROOT


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    org.runtime.resources.reset()
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
    org.define_service(ROOT, "ceo", "weekly", add_acceptance=["Sourced"], words="Sourced, please.")
    org.revise_playbook("ceo", "weekly", "first", "first version", [], text="1. Do the thing.")
    org.retire_service(ROOT, "ceo", "weekly", "not needed")
    kinds = [e["kind"] for e in read_events(org) if e["kind"].startswith("service.")]
    assert kinds == ["service.define", "service.define", "service.revise", "service.retire"]
    first, second = read_events(org, "service.define")
    assert (first["owner"], first["service"], first["version"], first["by"], first["amendment"]) == ("ceo", "weekly", 1, "root", False)
    assert second["version"] == 2 and second["amendment"] is True
    (rev,) = read_events(org, "service.revise")
    assert rev["version"] == 1 and rev["by"] == "ceo" and rev["owner"] == "ceo" and rev["admitted"] == "first"


# ---------------------------------------------------------------------------------------------------- the actor of a runtime write (design 4.2)
def revise_event(by, version=1, archive=None):
    from pathlib import Path

    from hirearchy.kernel import OrgPaths
    from hirearchy.kernel.testing import FakeClock, ListEventSink
    from hirearchy.services._places import OrgServicePlaces
    from hirearchy.services._texts import EventedPlaybookWriter
    from hirearchy.services.testing import MemoryServiceStore

    events = ListEventSink()
    writer = EventedPlaybookWriter(MemoryServiceStore(OrgServicePlaces(OrgPaths(Path("/org")))), FakeClock(), events)
    writer.write("ceo", "brief", version, "Steps.", by, "r", archive)
    (event,) = events.events
    return event


def test_a_runtime_write_emits_service_revise_with_actor_runtime_and_the_label_in_by():
    from hirearchy.services._items import RUNTIME_MIGRATION, RUNTIME_WATCH

    assert (RUNTIME_WATCH, RUNTIME_MIGRATION) == ("runtime (watch)", "runtime (migration)")
    for label in (RUNTIME_WATCH, RUNTIME_MIGRATION):
        event = revise_event(label)
        assert (event.kind, event.actor) == ("service.revise", "runtime")
        assert event.fields == {"owner": "ceo", "service": "brief", "version": 1, "by": label, "admitted": "client"}  # the fields are unchanged


def test_an_owners_and_roots_write_keep_actor_equal_to_by():
    for by in ("ceo", "root", "ceo/eng"):
        event = revise_event(by)
        assert event.actor == by and event.fields["by"] == by
