"""PLAN FOR YOU for a change to the organization (design 5.3) and its details."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from testkit.reach.hirearchy.core import ROOT

from hirearchy.blueprint._plan_texts import PLAN_END, PLAN_SHOW
from hirearchy.blueprint._shapes import RootTask

from ._extension_world import World, extension, world

TASK = RootTask("t1", datetime(2026, 11, 1, tzinfo=timezone.utc), ("- Every row has a date.",))


@pytest.fixture
def w(tmp_path: Path) -> World:
    """lead (4 reports at most, 1 now: writer) offers weekly (9 runs) and daily (9); solo offers nothing; old is a top-level agent nobody names."""
    made = world(tmp_path, lead_reports=4)
    for name in ("weekly", "daily"):
        made.org.define_service(
            ROOT, "lead", name, description=f"A {name} note", inputs=[], acceptance=["Every row has a date.", "At most 3 pages."],
            deliverable={"description": "a note"}, budget=9, playbook="steps",
        )
    made.org.hire(ROOT, "old", "Old", "x", tools=["read"])
    return made.using(tasks=[TASK])


def everything() -> dict[str, object]:
    return {
        **extension(
            add_agents=[{"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"],
                         "charter_extra": "Check every date item by item. Then report n of m."}],
            add_services=[{"owner": "solo", "name": "monthly", "description": "A monthly note",
                           "acceptance": [{"text": "Every row has a date.", "from_tasks": ["t1"]}, {"text": "At most 3 pages.", "default": True}],
                           "deliverable": {"description": "a note", "format": "markdown"}}],
            add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}],
            limits=[{"agent": "lead", "max_children": 6}, {"org": "max_depth", "value": 5}],
            budgets=[{"owner": "lead", "service": "weekly", "budget": 14}],
            retire=[{"agent": "old", "reason": "no longer needed"}],
            retire_services=[{"owner": "lead", "service": "daily", "reason": "unused"}],
        ),
        "reason": "B2.1: three failures on one criterion",
        "needs": {"elicitation": "Monthly notes, please. At most 3 pages."},
    }


EXPECTED = """\
PLAN FOR YOU (a change to your organization)
Why: B2.1: three failures on one criterion
Your organization now: 4 agents, 2 service(s): daily, weekly.
Adds:
- lead/checker (Independent Reviewer, model claude-sonnet-5.5, reports to lead): can read files only in <TMP>/src, <TMP>/ws/w and the organization's own files; cannot change your files
- service monthly of solo: A monthly note
  You provide: nothing: every request is the same. Each request: up to 4 runs, sent only when you ask.
  Checks:
    1. Every row has a date.
       my wording, from the one-off tasks I sent for you (2026-11-01); you accepted those deliveries
    2. At most 3 pages.
       my default: you did not say this
  Delivered to: inside the organization folder (no location given)
Changes:
- lead: may have up to 6 direct reports (was 4), so it may add 4 worker(s) without asking you
- the charter of lead/writer gets the line: "Cite the source."
- the charter of lead gets the line: "lead/checker (Independent Reviewer) was added to your team to check weekly: Check every date item by item."
- lead is told that lead/checker joined its team (one run of lead when it next runs)
- weekly of lead: up to 14 runs per request (was 9)
- the organization's depth: up to 5 levels (was 4)
Removes:
- service daily of lead: no new requests; its contract, playbook and cases are kept (defining it again continues them)
- old and its team (1 agents): its open tasks are closed as failed; its unspent runs come back.
Budget: weekly of lead: up to 14 runs per request (was 9); monthly of solo: up to 4 runs per request; nothing else changes what a request costs.
Unchanged: 1 agents and 0 service(s), their charters, contracts and playbooks.
Nothing changes until you approve. Reply 'approve', or tell me what to change."""


def test_the_block_is_5_3s_text_for_a_change_with_every_group(w: World) -> None:
    assert w.plan(everything()) == EXPECTED


def test_empty_groups_are_left_out(w: World) -> None:
    block = w.plan(extension(limits=[{"agent": "lead", "max_children": 6}]))
    assert block.splitlines() == [
        "PLAN FOR YOU (a change to your organization)", "Why: B1.1: a change", "Your organization now: 4 agents, 2 service(s): daily, weekly.",
        "Changes:", "- lead: may have up to 6 direct reports (was 4), so it may add 5 worker(s) without asking you",
        "Unchanged: 3 agents and 2 service(s), their charters, contracts and playbooks.",
        "Nothing changes until you approve. Reply 'approve', or tell me what to change.",
    ]
    for gone in ("Adds:", "Removes:", "Budget:"):
        assert gone not in block


def test_the_free_place_clause_appears_only_with_free_places(w: World) -> None:
    exact = w.plan(extension(limits=[{"agent": "lead", "max_children": 2}]))  # was 4: a lower limit, one place left (the writer is the one report)
    assert "- lead: may have up to 2 direct reports (was 4), so it may add 1 worker(s) without asking you" in exact
    full = w.plan(extension(
        add_agents=[{"parent": "lead", "name": "a", "template": "reviewer", "tools": ["read"]}, {"parent": "lead", "name": "b", "template": "reviewer", "tools": ["read"]}],
        limits=[{"agent": "lead", "max_children": 3}], budgets=[{"owner": "lead", "service": "weekly", "budget": 20}, {"owner": "lead", "service": "daily", "budget": 20}],
    ))
    assert "- lead: may have up to 3 direct reports (was 4)" in full and "worker(s)" not in full
    nothing = w.plan(extension(limits=[{"agent": "solo", "can_hire": True, "max_children": 0}]))
    assert "- solo: may have up to 0 direct reports (was 0); may hire: yes (was no)" in nothing and "worker(s)" not in nothing


def test_a_verifier_under_an_owner_lists_the_owners_line_and_that_it_is_told(w: World) -> None:
    block = w.plan(extension(
        add_agents=[{"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"]}], limits=[{"agent": "lead", "max_children": 6}],
        budgets=[{"owner": "lead", "service": "weekly", "budget": 14}, {"owner": "lead", "service": "daily", "budget": 14}],
    ))
    assert '- the charter of lead gets the line: "lead/checker (Independent Reviewer) was added to your team to check daily, weekly."' in block
    assert "- lead is told that lead/checker joined its team (one run of lead when it next runs)" in block
    assert "told" not in w.plan(extension(add_agents=[{"parent": "solo", "name": "c", "template": "reviewer", "tools": ["read"]}],
                                          limits=[{"agent": "solo", "can_hire": True, "max_children": 1}]))


def test_an_added_services_criteria_carry_their_source_lines(w: World) -> None:
    bp = everything()
    block = w.plan(bp)
    assert "my wording, from the one-off tasks I sent for you (2026-11-01); you accepted those deliveries" in block
    bp["needs"] = {"elicitation": "At most 3 pages. Notes, please."}
    quoted = bp["extend"]["add_services"][0]  # type: ignore[index]
    quoted["acceptance"] = [{"text": "Notes in at most 3 pages and plain words.", "from": "At most 3 pages.", "asked": "How long?"}]
    line = w.plan(bp)
    assert 'from your words "At most 3 pages." (my question: "How long?"); words I added: notes, in, and, plain, words' in line


def test_details_hold_the_resolved_entries_the_charters_and_the_fingerprint(w: World) -> None:
    text = w.planner().plan(everything(), allowed_roots=[w.tmp])
    assert text.issues == [] or all(i.level == "warning" for i in text.issues)
    d = text.details.replace(str(w.tmp), "<TMP>")
    assert d.startswith("Extension: B2.1: three failures on one criterion\nPlan id: ")
    assert "Added agent lead/checker: role Independent Reviewer; kind verifier; model claude-sonnet-5.5; tools read;" in d
    assert "Charter of lead/checker:\n" in d and "## Assignment (from the user's change " in d and "Reports to: lead" in d
    assert "## Additional instructions\nCheck every date item by item. Then report n of m." in d
    assert "Added service monthly of solo: 4 runs per request; criteria 2" in d
    assert "Limit lead: max_children 4 -> 6" in d and "Depth: max_depth 4 -> 5" in d
    assert "Retire old (team old): no longer needed" in d and "Retire service daily of lead: unused" in d
    assert "Fingerprint of the organization it touches: {" in d


def test_errors_make_a_draft_without_plan_id(w: World) -> None:
    bad = extension(add_agents=[{"parent": "ghost", "name": "x", "template": "reviewer"}])
    text = w.planner().plan(bad, allowed_roots=[w.tmp])
    assert text.block.splitlines()[0].startswith("DRAFT - NOT READY") and "Errors (1):" in text.block and text.block.endswith("Cannot apply yet.")
    assert "Plan id: (none: the extension has errors)" in text.details
    proposed = w.org.runtime.plan_renderer.propose_text(bad, target="Target organization: x", allowed_roots=[w.tmp], require_sources=True)
    assert proposed.endswith("plan_id: none (the blueprint has errors). Fix them and call propose_org again; do not ask the user to approve this.")
    assert PLAN_SHOW not in proposed and PLAN_END in proposed


def test_propose_text_of_an_extension_is_the_block_the_details_and_the_plan_id(w: World) -> None:
    good = extension(limits=[{"agent": "lead", "max_children": 6}])
    proposed = w.org.runtime.plan_renderer.propose_text(good, target="Target organization: x", allowed_roots=[w.tmp], require_sources=True)
    parts = proposed.split("\n\n")
    assert parts[0] == "Target organization: x" and parts[1] == PLAN_SHOW and parts[2].startswith("PLAN FOR YOU (a change to your organization)")
    pid = w.org.runtime.plan_identity.plan_id(good)
    assert f'apply_org(blueprint=<this exact YAML>, approved=True, plan_id="{pid}")' in proposed and f"plan_id: {pid}\n" in proposed
    assert 'propose_org(blueprint, extend="current") again' in proposed
    assert w.org.runtime.plan_renderer.plan_for_user(good, allowed_roots=[w.tmp]).startswith("PLAN FOR YOU (a change")
    assert "Limit lead: max_children 4 -> 6" in w.org.runtime.plan_renderer.render_plan(good, allowed_roots=[w.tmp])
