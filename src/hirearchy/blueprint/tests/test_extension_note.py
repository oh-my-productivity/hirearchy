"""The owner of a service is told of a new checker only after a full apply (design 5.5 step 9, L23)."""

from __future__ import annotations

from pathlib import Path

import pytest
from testkit.reach.hirearchy.app import wiring
from testkit.reach.hirearchy.core import ROOT, OrgError

from hirearchy.blueprint import BlueprintError
from hirearchy.blueprint.testing import FlakyHiring
from hirearchy.blueprint._protocols import OwnerNotes
from hirearchy.hierarchy import Hiring
from hirearchy.kernel import RUNTIME, EventSink
from hirearchy.kernel.testing import ListEventSink

from ._extension_world import World, extension, world

CRITERIA = ["Every row has a date.", "At most 3 pages."]


@pytest.fixture
def w(tmp_path: Path) -> World:
    made = world(tmp_path)
    made.org.define_service(ROOT, "lead", "weekly", description="A weekly note", inputs=[], acceptance=CRITERIA, deliverable={"description": "a note"}, budget=9, playbook="steps")
    return made


def plan() -> dict[str, object]:
    return {
        **extension(
            add_agents=[{"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"], "charter_extra": "Check C2 of weekly on every request. See R1 and R3."}],
            budgets=[{"owner": "lead", "service": "weekly", "budget": 20}], limits=[{"agent": "lead", "max_children": 3}],
        ),
        "reason": "B2.1: 3 cases failed C2",
    }


class RefusingNotes(OwnerNotes):
    def tell(self, to: str, title: str, body: str) -> None:
        raise OrgError("the inbox of lead is not writable")


def test_the_owner_gets_a_checker_joined_your_team_note_with_the_derived_step(w: World) -> None:
    w.org.runtime.extension_applier.apply(plan(), plan_id=None, allowed_roots=[w.tmp])
    notes = [m for m in w.org.messages("lead", "inbox") if m.title == "A checker joined your team"]
    assert len(notes) == 1
    (note,) = notes
    assert (note.sender, note.type, note.wake) == (RUNTIME, "note", True)
    assert note.body == (
        "lead/checker (Independent Reviewer) joined your team to check weekly.\n"
        'Add its step to the playbook of weekly: revise_playbook(op="add", kind="step", text="Before you report a request of weekly, send the draft to '
        'lead/checker and apply its FAIL items for C2.", evidence=["R1", "R3"])'
    )


def test_no_note_is_sent_after_an_undo(w: World) -> None:
    runtime = wiring.open_runtime(w.org.root, {Hiring: FlakyHiring(w.org.runtime.hiring, fail_on=1)})
    with pytest.raises(BlueprintError):
        runtime.extension_applier.apply(plan(), plan_id=None, allowed_roots=[w.tmp])
    assert [m for m in w.org.messages("lead", "inbox") if m.title == "A checker joined your team"] == []


def test_an_undeliverable_note_leaves_the_extension_applied_and_emits_team_note_failed(w: World) -> None:
    events = ListEventSink()
    runtime = wiring.open_runtime(w.org.root, {OwnerNotes: RefusingNotes(), EventSink: events})
    reply = runtime.extension_applier.apply(plan(), plan_id=None, allowed_roots=[w.tmp])
    assert "lead/checker" in w.org.agents() and "(lead was not told: the inbox of lead is not writable)" in reply
    (failed,) = [e for e in events.events if e.kind == "team_note.failed"]
    assert (failed.fields["owner"], failed.fields["agent"], failed.fields["error"]) == ("lead", "lead/checker", "the inbox of lead is not writable")


def test_a_change_without_a_new_verifier_tells_nobody(w: World) -> None:
    w.org.runtime.extension_applier.apply(extension(add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}]), plan_id=None, allowed_roots=[w.tmp])
    assert [m for m in w.org.messages("lead", "inbox") if m.title == "A checker joined your team"] == []
