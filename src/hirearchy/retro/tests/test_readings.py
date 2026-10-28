"""The readings of the brief (design 4.3): what was said (D1), what got past a check (D2), the rejections with no criterion yet (D3), the alarms and the causes to
settle (D4), the work asked for again and again (D5) and the idle or stranded agents (D6). Pure functions over narrow views; each section is capped in the block and
in Details, and a service whose record cannot be read has a line of its own."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fractions import Fraction

from hirearchy.reflection import CostAlarm, CostCase, RepeatAlarm
from hirearchy.retro import RetroThresholds
from hirearchy.retro._readings import d1_said, d2_passed, d3_unlinked, d4_alarms, d5_repeated, d6_health
from hirearchy.retro._shapes import groups
from hirearchy.retro._views import Answering, HealthFlag, OneOffCase, Passed, Said, ServiceAlarms

AT = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
THRESHOLDS = RetroThresholds()


def said(ref: str, words: str = "Too long.", *, service: str = "memos", link: str = "", answering: Answering | None = None, **more: object) -> Said:
    return Said(service, ref, "M1", AT, words, link, answering=answering, **more)  # type: ignore[arg-type]


def passed(case: str, *, signer: str = "ceo/checker", verifier: bool = True, cause: str = "contract-gap", also: tuple[str, ...] = (), **more: object) -> Passed:
    return Passed("memos", case, f"T-{case}", signer, verifier, ("R3",), ("C4",), cause, also, AT, "Not what I meant.", **more)


# ------------------------------------------------------------------------------ D1


def test_d1_lists_every_human_rejection_with_its_words_and_its_answer() -> None:
    rows = [
        said("R1", "Add the date.", link="confirmed", answering=Answering(4, ("C9",), ())),
        said("R2", "Say who owns it.", link="confirmed", about=("C3",), answering=Answering(5, (), ())),
        said("R3", "Too wordy.", link="confirmed", answering=Answering(6, ("C10",), ("C6",))),
        said("R4", "Drop that.", link="confirmed", answering=Answering(7, (), ("C7",))),
        said("R5", "Just this once.", link="none"),
        said("R6", "Same again.", link="confirmed", same_as="R2"),
        said("R7", "Do it in the old way.", service=""),
        said("R8", "Hmm."),
        said("R9", "Shorter.", link="confirmed", about=("C2",)),
    ]
    section = d1_said(rows, 0, [])
    assert (section.key, section.heading) == ("d1", "What you said")
    assert section.block == (
        '- memos R1: "Add the date." (C9 added (v4))', '- memos R2: "Say who owns it." (clarified C3 (v5))', '- memos R3: "Too wordy." (removed C6 (replaced by C10))',
        '- memos R4: "Drop that." (removed C7)', '- memos R5: "Just this once." (no lasting rule)', "- and 4 more (Details)",
    )
    assert section.details[5:] == (
        '- memos R6 (case M1, 2026-11-02): "Same again." (same as R2)', '- one-off R7 (case M1, 2026-11-02): "Do it in the old way." (one-off)',
        '- memos R8 (case M1, 2026-11-02): "Hmm." (no answer yet)', '- memos R9 (case M1, 2026-11-02): "Shorter." (about C2)',
    )
    assert section.details[2] == '- memos R3 (case M1, 2026-11-02): "Too wordy." (removed C6 (replaced by C10))' and section.counts == (("rejections", 9), ("accepts", 0))


def test_an_answer_that_changes_no_criterion_and_names_none_reads_answered() -> None:
    row = said("R2", "Say who owns it.", link="confirmed", answering=Answering(5, (), ()))
    assert d1_said([row], 0, []).block == ('- memos R2: "Say who owns it." (answered (v5))',)


def test_d1_counts_the_accepts() -> None:
    section = d1_said([said("R1")], 3, [])
    assert section.block[-1] == "- and 3 accepts" and section.details[-1] == "- and 3 accepts" and ("accepts", 3) in section.counts
    assert d1_said([], 1, []).block == ("- and 1 accepts",)


def test_d1_cuts_the_words_in_the_block_and_not_in_details() -> None:
    long = "w" * 150
    section = d1_said([said("R1", long)], 0, [])
    assert section.block == (f'- memos R1: "{"w" * 119}…" (no answer yet)',) and long in section.details[0]


def test_d1_with_nothing_reads_none() -> None:
    section = d1_said([], 0, [])
    assert section.block == section.details == ("- none",) and section.counts == (("rejections", 0), ("accepts", 0))


# ------------------------------------------------------------------------------ D2


def test_d2_names_a_verifier_signer_and_a_signer_that_is_no_check() -> None:
    section = d2_passed([passed("M1"), passed("M2", signer="ceo/writer", verifier=False)], [])
    assert section.block == (
        "- memos: ceo/checker passed M1; you rejected it (R3, C4)",
        "- memos: ceo/writer delivered M2 (no check of the team signed it); you rejected it (R3, C4)",
    )
    assert section.counts == (("escapes", 2), ("passed_by_a_check", 1), ("no_check_signed", 1))


def test_d2_shows_a_disputed_causes_also_types() -> None:
    section = d2_passed([passed("M1", cause="reviewer-miss", also=("contract-gap",))], [])
    assert section.details == ("- memos: ceo/checker passed M1; you rejected it (R3, C4); cause reviewer-miss, also contract-gap",)
    assert d2_passed([passed("M1")], []).details == ("- memos: ceo/checker passed M1; you rejected it (R3, C4); cause contract-gap",)


# ------------------------------------------------------------------------------ D3


def test_d3_lists_unconfirmed_and_removed_only_assertions() -> None:
    rows = [
        said("R1", "A.", link="confirmed", about=("C1",), current_about=("C1",)),
        said("R2", "B.", link="unconfirmed"),
        said("R3", "C.", link="none"),
        said("R4", "D.", link="confirmed", about=("C6",), removed_about=("C6",)),
        said("R5", "E.", link=""),
        said("R6", "F.", link="confirmed", about=("C2", "C6"), current_about=("C2",), removed_about=("C6",)),
        said("R7", "G.", link="confirmed"),
    ]
    section = d3_unlinked(rows, [])
    assert section.block == () and section.counts == (("without_a_criterion", 5),)
    assert section.details == (
        '- memos R2: "B." (unconfirmed)', '- memos R3: "C." (no lasting rule)', '- memos R4: "D." (about removed C6 only)', '- memos R5: "E." (unconfirmed)',
        '- memos R7: "G." (about no criterion)',
    )
    assert d3_unlinked([], []).details == ("- none",)


# ------------------------------------------------------------------------------ D4


def test_d4_gives_both_alarms_by_lineage_and_each_untyped_or_disputed_cause() -> None:
    repeat = RepeatAlarm("fires", 3, ("M1", "M2", "M3"), (("C10", 2),), ("C10",), (("C10", ("M1", "M2")),), (), (("C10", ("C6", "C10")),))
    cost = CostAlarm("fires", 3, 3, (CostCase("M2", 9, 6, 0, 9),))
    quiet = ServiceAlarms("notes", RepeatAlarm("n/a", 2), CostAlarm("n/a", 2))
    rows = [ServiceAlarms("memos", repeat, cost), quiet]
    escapes = [passed("M1", cause="untyped"), passed("M2", cause="reviewer-miss", also=("contract-gap",)), passed("M3")]
    section = d4_alarms(rows, escapes, [])
    assert section.details[:3] == (
        "- memos: repeat alarm fires: C10 (and its earlier wording C6) in 2 of 3 judged cases",
        "- memos: cost alarm fires: M2 used 9 runs against 6 approved",
        "- notes: repeat alarm n/a (2 judged cases); cost alarm n/a (2 judged cases)",
    )
    assert section.details[3] == '- R3 (memos, 2026-11-02): "Not what I meant.". Was it a gap in the criteria (the team met them), a check that missed it, or a one-off?'
    assert section.details[4] == "- R3 (memos): the rules read it as reviewer-miss and as contract-gap. Was it a check that missed it?"
    assert len(section.details) == 5 and section.counts == (("alarms_firing", 2), ("untyped_causes", 1), ("disputed_causes", 1))


def test_d4_with_nothing_reads_none() -> None:
    assert d4_alarms([], [], []).details == ("- none",)
    assert d4_alarms([ServiceAlarms("memos", RepeatAlarm("no", 4), CostAlarm("no", 4, 4))], [], []).details == (
        "- memos: repeat alarm no (4 judged cases); cost alarm no (4 judged cases)",
    )


# ------------------------------------------------------------------------------ D5


def one(case_id: str, title: str, *criteria: str, judged: bool = True, assignee: str = "lead") -> OneOffCase:
    return OneOffCase(case_id, assignee, title, tuple(criteria), judged=judged)


def test_d5_groups_with_their_relation_and_count_and_unjudged_tasks_apart() -> None:
    cases = [
        one("M1", "Action list for 2026-11-02", "Every action has an owner"), one("M2", "Action list for 2026-11-09", "Nothing to see"),
        one("M3", "Action list for 2026-11-16", "Else", judged=False), one("M4", "Alone", "Something unique"),
    ]
    found = groups(cases, Fraction("0.6"))
    section = d5_repeated(found, [], THRESHOLDS)
    assert section.details == (
        '- lead: "Action list for 2026-11-02" and 2 more (M1, M2, M3), joined by their titles: 2 of 3 with your verdict',
        "  1 more without your verdict, not counted",
    )
    assert section.counts == (("shape_groups", 1), ("largest_group_judged", 2))
    assert d5_repeated([], [], THRESHOLDS).details == ("- none",)


def test_d5_says_when_an_assignee_is_not_top_level() -> None:
    found = groups([one("M1", "Same", assignee="ceo/lead"), one("M2", "Same", assignee="ceo/lead")], Fraction("0.6"))
    assert d5_repeated(found, [], THRESHOLDS).details[0].endswith("assignee ceo/lead is not a top-level agent")


# ------------------------------------------------------------------------------ D6


def test_d6_lists_the_health_flags() -> None:
    flags = [HealthFlag("ceo/writer", "idle", "no open task and no activity for 2d", 4), HealthFlag("ceo/checker", "stranded_budget", "no work for 40m", 3)]
    section = d6_health(flags, [])
    assert section.details == (
        "- ceo/writer (idle): no open task and no activity for 2d; holds 4 unspent runs", "- ceo/checker (stranded_budget): no work for 40m; holds 3 unspent runs",
    )
    assert d6_health([], []).details == ("- none",) and d6_health([], ["- ceo/x: idle, owns notes: kept"]).details == ("- ceo/x: idle, owns notes: kept",)


# ------------------------------------------------------------------------------ caps and unreadable services


def test_each_section_is_capped_in_the_block_and_in_details() -> None:
    rows = [said(f"R{n}") for n in range(1, 31)]
    section = d1_said(rows, 0, [])
    assert len(section.block) == 6 and section.block[-1] == "- and 25 more (Details)"
    assert len(section.details) == 21 and section.details[-1] == "- and 10 more: retro(since=...) lists them all for a shorter window"
    assert d2_passed([passed(f"M{n}") for n in range(8)], []).block[-1] == "- and 3 more (Details)"


def test_an_unreadable_service_reads_cannot_be_read_and_gives_no_candidate() -> None:
    broken = [("notes", "the contract cannot be parsed")]
    line = "- notes: cannot be read (the contract cannot be parsed)"
    for section in (d1_said([], 0, broken), d2_passed([], broken), d3_unlinked([], broken), d4_alarms([], [], broken)):
        assert section.details[-1] == line and section.details != (line, "- none") and "- none" not in section.details
    assert d1_said([said("R1")], 0, broken).block[-1] == line
    assert d6_health([HealthFlag("a", "idle", "r", None)], []).details == ("- a (idle): r",)


# ------------------------------------------------------------------------------ D9 to D14 (commit 43)

from testkit.reach.hirearchy.observability._pure import is_error  # noqa: E402

from hirearchy.retro import Item  # noqa: E402
from hirearchy.retro._facts import proposals_of  # noqa: E402
from hirearchy.retro._readings import d9_criteria, d10_proposals, d11_playbooks, d12_spend, d13_last, d14_held  # noqa: E402
from hirearchy.retro._views import Fate, PlaybookFacts, ProposalFacts, Refusal, Sourced, SpendFacts, WatchRetire  # noqa: E402


def sourced(cid: str, kind: str, **more: object) -> Sourced:
    return Sourced("memos", cid, "Every action has an owner", kind, exercised=5, accepted=4, **more)  # type: ignore[arg-type]


def test_d9_shows_each_sourced_criterion_with_its_quote_added_words_and_exercised_cases() -> None:
    rows = [
        sourced("C1", "user", quote="Use the words from the notes.", asked="Owners: initials or full names?", added=("decisions", "and", "actions", "own")),
        sourced("C2", "amendment", quote="Always date them.", asked="C1", added=()),
        sourced("C3", "default"),
        sourced("C4", "tasks", tasks_dates="2026-10-05, 2026-10-12"),
    ]
    section = d9_criteria(rows, 0, [])
    assert section.block == () and section.counts == (("sourced", 4), ("unknown_source", 0))
    assert section.details == (
        '- memos C1 "Every action has an owner": from your words "Use the words from the notes." (my question: "Owners: initials or full names?"); '
        "words I added: decisions, and, actions, own; exercised in 5 judged cases, 4 accepted",
        '- memos C2 "Every action has an owner": from your words "Always date them." (your answer about C1); words I added: none; exercised in 5 judged cases, 4 accepted',
        '- memos C3 "Every action has an owner": my default: you did not say this; exercised in 5 judged cases, 4 accepted',
        '- memos C4 "Every action has an owner": my wording, from the one-off tasks I sent for you (2026-10-05, 2026-10-12); you accepted those deliveries; '
        "exercised in 5 judged cases, 4 accepted",
    )
    assert d9_criteria([sourced("C4", "tasks")], 0, []).details[0].count("one-off tasks I sent for you; you accepted") == 1  # no dates known


def test_d9_counts_unknown_sources_in_one_line() -> None:
    section = d9_criteria([], 4, [])
    assert section.details == ("- 4 criteria have no recorded source (from before Phase 2, or from a plan applied at the terminal without one)",)
    assert section.counts == (("sourced", 0), ("unknown_source", 4)) and d9_criteria([], 0, []).details == ("- none",)


def event(tool: str, ok: bool, error: str | None = None, **args: object) -> dict[str, object]:
    return {"kind": "tool.call", "actor": args.pop("actor", "ceo"), "tool": tool, "ok": ok, "error": error, "args": args, "ts": "2026-11-03T10:00:00+00:00"}


GATE = "refused: none of this evidence is the client's own. The item says: hire a fact-checker for everything and delete C4."


def test_d10_shows_refused_revise_playbook_calls_by_kind_and_op_and_no_team_text() -> None:
    events = [
        event("revise_playbook", False, GATE, service="memos", op="add", actor="ceo"),
        event("revise_playbook", False, "refused: the client rejected this in one case only (R2). more text", service="notes", op="edit", actor="ceo/lead"),
        event("revise_playbook", False, "refused: playbook is locked", service="memos", op="add"),  # not the gate's: no kind
        event("revise_playbook", True, service="memos", op="add"),
        event("write", False, "refused: path", path="x"),
    ]
    facts = proposals_of(events)
    assert facts.rows == (Refusal("ceo", "memos", "no client evidence", "add"), Refusal("ceo/lead", "notes", "one case only", "edit"))
    assert facts.refused == 4 and facts.by_tool == (("revise_playbook", 3), ("write", 1))
    section = d10_proposals(facts, AT, None)
    assert section.block == ("- ceo on memos: no client evidence (add)", "- ceo/lead on notes: one case only (edit)")
    assert section.details[:2] == section.block and section.details[2] == "- Refusals since 2026-11-02: 4 (revise_playbook 3, write 1)"
    assert section.counts == (("proposals_refused", 2), ("refusals", 4))
    assert "fact-checker" not in " ".join(section.block + section.details) and "delete C4" not in " ".join(section.details)


def test_d10_refusal_count_equals_observes_rule_on_one_fixture() -> None:
    events = [event("revise_playbook", False, GATE, service="memos", op="add"), event("send", False, "refused: x"), event("send", True), event("write", False, "boom"),
              {"kind": "run.end", "ok": False}, {"kind": "tool.call", "tool": "read", "ok": True}]
    assert proposals_of(events).refused == sum(1 for ev in events if ev.get("kind") == "tool.call" and is_error(ev)) == 3


def test_d10_blocks_at_most_3_lines_and_beyond_the_event_horizon_says_events_expired() -> None:
    facts = ProposalFacts(tuple(Refusal("ceo", f"s{n}", "no client evidence", "add") for n in range(5)), 5, (("revise_playbook", 5),))
    section = d10_proposals(facts, datetime(2026, 10, 1, tzinfo=timezone.utc), datetime(2026, 10, 20, tzinfo=timezone.utc))
    assert len(section.block) == 4 and section.block[-1] == "- and 2 more (Details)"
    assert section.details[-1] == "- events before 2026-10-20 have expired (events_keep_days)"
    assert d10_proposals(ProposalFacts(), AT, AT - timedelta(days=1)).details == ("- Refusals since 2026-11-02: 0",)


def test_d11_gives_words_of_cap_mirror_items_and_each_watch_retire_by_refinement_direct_or_mixed() -> None:
    refined = WatchRetire("P3", 6, (), "", ("R4",), (("C6", "C10"),))
    direct = WatchRetire("P4", 7, ("R5", "R6"), "C2", (), ())
    mixed = WatchRetire("P5", 8, ("R7",), "C3", ("R8",), (("C1", "C11"),))
    rows = [PlaybookFacts("memos", 640, 1000, (("warning", 1), ("kept", 3)), ("P2",), ("P1", "P6"), 31, (refined, direct, mixed)), PlaybookFacts("notes", 0, 1000)]
    section = d11_playbooks(rows, [])
    assert section.details == (
        "- memos: 640 of 1000 words; items: 1 warning, 3 kept; 1 retire candidate (P2); 2 mirror items repeat 31 words of the contract (P1, P6)",
        "- memos: P3 retired by the watch in v6 because a refinement of the criterion it carries was rejected (R4: the answers replaced C6 with C10); its wording is now only in the contract.",
        "- memos: P4 retired by the watch in v7: R5, R6 rejected deliveries on C2 it carries.",
        "- memos: P5 retired by the watch in v8: R7 rejected deliveries on C3 it carries; and because a refinement of the criterion it carries was rejected "
        "(R8: the answers replaced C1 with C11); its wording is now only in the contract.",
        "- notes: 0 of 1000 words; no playbook items",
    )
    assert d11_playbooks([], []).details == ("- none",)


def test_d12_states_the_approved_basis_of_2a() -> None:
    section = d12_spend([SpendFacts("memos", 6, 40, 6, 2), SpendFacts("notes", 0, 0, 0, 0)], [])
    assert section.details == (
        "- approved = root's hand-downs (the user's own approvals are not recorded; F-P1-10)",
        "- memos: 6 cases, 40 runs used against 6 approved per request; 2 cases above it",
        "- notes: 0 cases",
    )


def test_d13_gives_each_last_item_taken_or_lapsed() -> None:
    fates = [Fate("B2.1", "service", "taken", "ceo/list defined"), Fate("B2.2", "checker-add", "lapsed", ""), Fate("B2.3", "retire", "open", "")]
    section = d13_last(fates, "B2")
    assert section.details == ("- B2.1 service: taken (ceo/list defined)", "- B2.2 checker-add: lapsed: no change", "- B2.3 retire: open")
    assert d13_last([], None).details == ("- no earlier brief",) and d13_last([], "B1").details == ("- B1 offered no item",)


def test_d14_lists_the_held_back_candidates() -> None:
    held = [Item("retire", "retire|ceo/x", ("A",), weight=0), Item("service", "service|ceo|M1", ("M1", "M2"), weight=2)]
    assert d14_held(held).details == ("- retire retire|ceo/x (weight 0)", "- service service|ceo|M1 (weight 2)") and d14_held([]).details == ("- none",)
