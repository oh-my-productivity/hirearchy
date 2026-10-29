"""The structural changes of the organization, their labels and the unprompted charter edits (design 4.5, D8).

The labels are read from what the files themselves record (``approved_in``, ``hired_by``, ``RETIRED.md``, the committed charters, the ``write`` events), never
from a commit message: a commit can hold another process's edit, and root's tool calls do not commit."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hirearchy.retro import BriefRecord, RecordedItem
from hirearchy.retro._changes import Change, ChangeFacts, changes_of
from hirearchy.retro._ports import CharterPair, CharterVersions, KeyChange
from hirearchy.retro._views import AgentFact, EffectFacts, EventFacts, RetiredFact, ServiceFact, ServiceRetired, WriteFact

START = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
SINCE = START - timedelta(days=1)


def at(minutes: int) -> datetime:
    return START + timedelta(minutes=minutes)


def agent(addr: str, minutes: int = 1, *, approved_in: str = "", hired_by: str = "root", plan_heading: bool = False, verifier: bool = False) -> AgentFact:
    return AgentFact(addr, at(minutes), hired_by, approved_in, "verifier" if verifier else "author", plan_heading, verifier)


def pair(addr: str, minutes: int, commit: str = "", **fields: object) -> CharterPair:
    path = "ORG.md" if addr == "ORG.md" else f"{addr}/AGENT.md"
    return CharterPair(path, commit or f"c{minutes}", at(minutes), older=at(minutes - 1), **fields)  # type: ignore[arg-type]


def run(facts: ChangeFacts, since: datetime | None = SINCE) -> list[Change]:
    return list(changes_of(facts, since).changes)


def only(facts: ChangeFacts, since: datetime | None = SINCE) -> Change:
    (found,) = changes_of(facts, since).changes
    return found


def charters(*pairs: CharterPair, **more: object) -> ChangeFacts:
    return ChangeFacts(versions=CharterVersions(True, pairs), **more)  # type: ignore[arg-type]


COVERED = EventFacts(covers_from=START - timedelta(days=3))


def wrote(actor: str, addr: str, minutes: int) -> WriteFact:
    return WriteFact(at(minutes) - timedelta(seconds=30), actor, f"{addr}/AGENT.md")


# ------------------------------------------------------------------------------ the creations and the retires


def test_an_agent_of_a_plan_reads_from_the_plan_you_approved() -> None:
    change = only(ChangeFacts(agents=(agent("ceo", approved_in="plan abc123"),)))
    assert (change.kind, change.subject, change.label) == ("agent-created", "ceo", "from the plan you approved (2026-11-02)") and not change.unprompted
    assert change.text == "agent ceo added (2026-11-02)" and change.line == "agent ceo added (2026-11-02): from the plan you approved (2026-11-02)"


def test_an_agent_from_before_phase_2_with_the_plan_heading_reads_from_the_plan_too() -> None:
    assert only(ChangeFacts(agents=(agent("ceo", plan_heading=True),))).label == "from the plan you approved (2026-11-02)"


def test_an_agent_of_an_extension_reads_from_your_change() -> None:
    change = only(ChangeFacts(agents=(agent("ceo/checker", approved_in="change fedcba654321", verifier=True),)))
    assert change.label == "from your change fedcba654321" and change.plan_id == "fedcba654321"


def test_an_agent_of_an_extension_that_is_the_effect_of_an_item_names_the_item() -> None:
    held = BriefRecord("B1", at(0), None, "mcp", (RecordedItem(1, "service", "service|ceo|M1", (), {"service": "ceo/list"}), RecordedItem(2, "checker-add", "checker-add|ceo|C4", (), {"owner": "ceo"})))
    checker = agent("ceo/checker", 5, approved_in="change fedcba654321", verifier=True)
    assert only(ChangeFacts(agents=(checker,), briefs=(held,))).label == "from your change fedcba654321, item B1.2"
    assert only(ChangeFacts(agents=(agent("ceo/other", 5, approved_in="change fedcba654321"),), briefs=(held,))).label == "from your change fedcba654321"  # not a verifier
    assert only(ChangeFacts(agents=(agent("ceo/checker", -5, approved_in="change fedcba654321", verifier=True),), briefs=(held,))).label == "from your change fedcba654321"  # before the brief


def test_a_lead_s_own_hire_reads_inside_the_plan_by_the_lead() -> None:
    change = only(ChangeFacts(agents=(agent("ceo/writer", hired_by="ceo"),)))
    assert change.label == "inside the plan, by ceo" and change.by == "ceo" and not change.unprompted


def test_root_s_hire_with_no_approval_reads_by_root_outside_a_plan() -> None:
    assert only(ChangeFacts(agents=(agent("ceo"),))).label == "by root, outside a plan (the terminal, or before this record was kept)"


def test_an_agent_the_undo_took_back_reads_taken_back() -> None:
    change = only(ChangeFacts(agents=(agent("ceo/checker", approved_in="change fedcba654321 (not applied)"),)))
    assert change.label == "taken back: the change fedcba654321 was not applied"


def test_a_retire_reads_its_record() -> None:
    plan = RetiredFact("ceo/old", at(3), "root", "idle for 2d (B1.1)", "change abc123", True)
    assert only(ChangeFacts(retired=(plan,))).line == "agent ceo/old retired (2026-11-02): from your change abc123"
    by_lead = RetiredFact("ceo/old", at(3), "ceo", "done", "", True)
    assert only(ChangeFacts(retired=(by_lead,))).label == "inside the plan, by ceo"
    by_root = RetiredFact("ceo/old", at(3), "root", "done", "", True)
    assert only(ChangeFacts(retired=(by_root,))).label == "by root, outside a plan (the terminal, or before this record was kept)"
    undone = RetiredFact("ceo/x", at(3), "root", "not applied", "change abc123 (not applied)", True)
    assert only(ChangeFacts(retired=(undone,))).label == "taken back: the change abc123 was not applied"


def test_a_tree_retired_before_phase_2_reads_retired_date_without_a_label() -> None:
    change = only(ChangeFacts(retired=(RetiredFact("ceo/old", at(3), "", "", "", False),)))
    assert change.text == change.line == "agent ceo/old retired 2026-11-02" and change.label == "" and not change.unprompted


def test_a_service_reads_like_an_agent() -> None:
    plan = ServiceFact("ceo", "list", at(1), "root", "plan abc123")
    assert only(ChangeFacts(services=(plan,))).label == "from the plan you approved (2026-11-02)"
    held = BriefRecord("B2", at(0), None, "cli", (RecordedItem(1, "service", "service|ceo|M1", (), {"service": "ceo/list"}),))
    change = only(ChangeFacts(services=(ServiceFact("ceo", "list", at(2), "root", "change fedcba654321"),), briefs=(held,)))
    assert change.label == "from your change fedcba654321, item B2.1" and change.text.startswith("service ceo/list added")
    assert only(ChangeFacts(services=(ServiceFact("ceo/lead", "x", at(1), "ceo/lead", ""),))).label == "inside the plan, by ceo/lead"
    assert only(ChangeFacts(services=(ServiceFact("ceo", "x", at(1), "root", ""),))).label.startswith("by root, outside a plan")
    gone = ServiceRetired("ceo", "list", at(4), "root", "revert", "change fedcba654321")
    assert only(ChangeFacts(retired_services=(gone,))).line == "service ceo/list retired (2026-11-02): from your change fedcba654321"


def test_a_service_the_user_renamed_names_the_item_that_offered_it_by_its_criteria() -> None:
    item = RecordedItem(1, "service", "service|ceo|M1", ("M1", "M2", "M3"), {"service": "ceo/list"})
    held = BriefRecord("B2", at(0), None, "cli", (item,))
    effects = EffectFacts(shapes={c: ("everyactionhasanowner",) for c in ("M1", "M2", "M3")}, defined=(("ceo", "chores", ("everyactionhasanowner",)),))
    renamed = ServiceFact("ceo", "chores", at(2), "root", "change fedcba654321")
    assert only(ChangeFacts(services=(renamed,), briefs=(held,), effects=effects)).label == "from your change fedcba654321, item B2.1"
    other = EffectFacts(shapes=effects.shapes, defined=(("ceo", "chores", ("somethingelse",)),))
    assert only(ChangeFacts(services=(renamed,), briefs=(held,), effects=other)).label == "from your change fedcba654321"  # another criteria key: not the item's service


def test_changes_before_since_are_left_out_and_the_rest_are_in_time_order() -> None:
    facts = ChangeFacts(agents=(agent("a", 30, approved_in="plan x"), agent("b", 10, approved_in="plan x"), agent("old", -3000, approved_in="plan x")))
    assert [c.subject for c in run(facts, at(0))] == ["b", "a"]
    assert [c.subject for c in run(facts, None)] == ["old", "b", "a"]


# ------------------------------------------------------------------------------ the charters


def test_an_extension_s_line_reads_from_your_change() -> None:
    line = pair("ceo/checker", 5, added_before=(), added_after=("- Check C4 [change fedcba654321]",))
    change = only(charters(line))
    assert change.label == "from your change fedcba654321" and not change.unprompted and change.kind == "charter"


def test_an_extension_s_line_that_is_the_effect_of_a_checker_fix_names_the_item() -> None:
    held = BriefRecord("B1", at(0), None, "mcp", (RecordedItem(3, "checker-fix", "checker-fix|s|v|C4", (), {"agent": "ceo/checker", "line": "Check C4 item by item."}),))
    line = pair("ceo/checker", 5, added_after=("- Check C4 item by item. [change fedcba654321]",))
    assert only(charters(line, briefs=(held,))).label == "from your change fedcba654321, item B1.3"


def test_the_limits_an_extension_names_read_from_your_change_and_other_values_do_not() -> None:
    limits = "- Your hiring limits were set by the user's change: up to 3 direct reports; may hire: yes. [change fedcba654321]"
    named = pair("ceo", 5, keys=(KeyChange("can_hire", "false", "true"), KeyChange("max_children", "2", "3")), added_after=(limits,))
    assert only(charters(named)).label == "from your change fedcba654321"
    other = pair("ceo", 5, keys=(KeyChange("max_children", "2", "9"),), added_after=(limits,))
    assert only(charters(other)).label == "outside the tools (a hand edit or the terminal)" and only(charters(other)).unprompted


def test_a_removed_tagged_line_is_the_extension_s_too() -> None:
    gone = pair("ceo/checker", 5, added_before=("- Check C4 [change aaa111]", "- Keep [change bbb222]"), added_after=("- Keep [change bbb222]",))
    assert only(charters(gone)).label == "from your change aaa111"


def test_a_line_without_a_tag_is_no_extension_s() -> None:
    untagged = pair("ceo/checker", 5, added_after=("- Be nice",))
    assert only(charters(untagged, events=COVERED)).unprompted


def test_a_leads_body_edit_with_its_write_event_reads_by_the_parent() -> None:
    edit = pair("ceo/writer", 5, body_differs=True)
    change = only(charters(edit, events=EventFacts((wrote("ceo", "ceo/writer", 5),), COVERED.covers_from)))
    assert change.label == "by ceo" and change.by == "ceo" and change.unprompted
    role = pair("ceo/writer", 5, keys=(KeyChange("role", "Writer", "Senior writer"),))
    assert only(charters(role, events=EventFacts((wrote("ceo", "ceo/writer", 5),), COVERED.covers_from))).label == "by ceo"
    lower = pair("ceo/writer", 5, keys=(KeyChange("max_children", "3", "2"),))
    assert only(charters(lower, events=EventFacts((wrote("ceo", "ceo/writer", 5),), COVERED.covers_from))).label == "by ceo"
    higher = pair("ceo/writer", 5, keys=(KeyChange("max_children", "2", "3"),))
    assert only(charters(higher, events=EventFacts((wrote("ceo", "ceo/writer", 5),), COVERED.covers_from))).label.startswith("outside the tools")


def test_a_write_by_another_actor_or_at_another_time_or_on_another_file_is_no_match() -> None:
    edit = pair("ceo/writer", 5, body_differs=True)
    for write in (wrote("root", "ceo/writer", 5), wrote("ceo", "ceo/writer", 50), wrote("ceo", "ceo/other", 5)):
        assert only(charters(edit, events=EventFacts((write,), COVERED.covers_from))).label == "outside the tools (a hand edit or the terminal)"


def test_a_write_in_the_same_second_as_the_commit_still_matches() -> None:
    edit = pair("ceo/writer", 5, body_differs=True)
    late = WriteFact(at(5) + timedelta(milliseconds=600), "ceo", "ceo/writer/AGENT.md")
    assert only(charters(edit, events=EventFacts((late,), COVERED.covers_from))).label == "by ceo"


def test_a_hand_edit_of_a_top_level_charter_reads_outside_the_tools() -> None:
    edit = pair("ceo", 5, body_differs=True)
    change = only(charters(edit, events=EventFacts((wrote("root", "ceo", 5),), COVERED.covers_from)))
    assert change.label == "outside the tools (a hand edit or the terminal)" and change.unprompted
    assert only(charters(pair("ceo/writer", 5, keys=(KeyChange("tools", None, '["read"]'),)), events=COVERED)).label.startswith("outside the tools")


def test_a_change_whose_window_is_beyond_the_event_log_reads_by_the_parent_or_outside_the_tools() -> None:
    edit = pair("ceo/writer", 5, body_differs=True)
    reaches = EventFacts((), at(5))  # the oldest event is after the older commit (minute 4)
    assert only(charters(edit, events=reaches)).label == "by ceo, or outside the tools (the event log does not reach back)"
    assert only(charters(edit)).label == "by ceo, or outside the tools (the event log does not reach back)"  # events off or empty
    assert only(charters(edit)).unprompted


def test_labels_come_from_content_not_from_commit_messages() -> None:
    edit = pair("ceo/writer", 5, commit="c9", body_differs=True)
    swept = pair("ceo/checker", 5, commit="c9", added_after=("- Check C4 [change fedcba654321]",))  # one commit, two writers
    found = {c.subject: c for c in run(charters(edit, swept, subjects={"c9": "root: applied extension fedcba654321"}, events=COVERED))}
    assert found["ceo/writer"].label == "outside the tools (a hand edit or the terminal)"  # the message does not make a body edit the user's change
    assert found["ceo/checker"].label == "from your change fedcba654321"
    flipped = run(charters(edit, swept, subjects={"c9": "ceo/writer: run 3"}, events=COVERED))
    assert {c.subject: c.label for c in flipped} == {c.subject: c.label for c in found.values()}


def test_the_unprompted_count_counts_the_three_unprompted_labels() -> None:
    events = EventFacts((wrote("ceo", "ceo/a", 5),), COVERED.covers_from)
    facts = charters(
        pair("ceo/a", 5, body_differs=True),  # by ceo
        pair("ceo/b", 6, body_differs=True),  # outside the tools
        pair("ceo/c", 7, added_after=("- X [change aaa111]",)),  # the user's change
        pair("top", 8, body_differs=True),  # outside the tools
        events=events,
    )
    done = changes_of(facts, SINCE)
    assert done.unprompted == 3 and sorted(c.label.split(" (")[0] for c in done.changes if c.unprompted) == ["by ceo", "outside the tools", "outside the tools"]
    uncovered = changes_of(charters(pair("ceo/a", 5, body_differs=True), events=EventFacts()), SINCE)
    assert uncovered.unprompted == 1 and uncovered.changes[0].label.startswith("by ceo, or outside the tools")


def test_a_deletion_a_recreated_address_and_retired_paths_are_not_edits() -> None:
    deleted = pair("ceo/old", 5, kind="deleted")
    created = pair("ceo/old", 6, kind="created")
    retired = CharterPair(".retired/ceo.old-20261102T090500/AGENT.md", "c7", at(7), older=at(6), body_differs=True)
    done = changes_of(charters(deleted, created, retired, events=COVERED), SINCE)
    assert done.changes == () and done.unprompted == 0


def test_a_max_depth_pair_is_attributed_by_its_commit_subject() -> None:
    made = pair("ORG.md", 5, commit="c1", depth=("4", "5"))
    other = pair("ORG.md", 8, commit="c2", depth=("5", "6"))
    done = changes_of(charters(made, other, subjects={"c1": "root: applied extension fedcba654321"}), SINCE)
    labels = {c.text: c.label for c in done.changes}
    assert labels == {
        "ORG.md max_depth 5 -> 6 (2026-11-02)": "outside the tools (a hand edit or the terminal)",
        "ORG.md max_depth 4 -> 5 (2026-11-02)": "from your change fedcba654321",
    }
    assert done.unprompted == 0  # a depth is a limit, not a charter edit
    assert done.changes[0].kind == "depth" and done.changes[0].plan_id == "fedcba654321"


def test_without_git_the_count_reads_unknown_and_truncated_n_or_more() -> None:
    nothing = changes_of(ChangeFacts(agents=(agent("ceo", approved_in="plan x"),)), SINCE)
    assert (nothing.known, nothing.unprompted, nothing.unprompted_text) == (False, None, "unknown")
    assert nothing.charter_line == "charter history unknown (no git history)" and len(nothing.changes) == 1  # creations and retires keep their labels
    cut = changes_of(ChangeFacts(versions=CharterVersions(True, (pair("ceo/a", 5, body_differs=True), pair("ceo/b", 6, body_differs=True)), truncated=True)), SINCE)
    assert (cut.known, cut.unprompted, cut.unprompted_text) == (True, 2, "2 or more (the history read stops at 40 commits)") and cut.charter_line == ""
    exact = changes_of(ChangeFacts(versions=CharterVersions(True, ())), SINCE)
    assert (exact.unprompted, exact.unprompted_text) == (0, "0")


def test_the_pairs_before_since_are_not_counted() -> None:
    old = pair("ceo/a", -3000, body_differs=True)
    assert changes_of(charters(old, events=COVERED), SINCE).unprompted == 0
    assert changes_of(charters(old, events=COVERED), None).unprompted == 1
