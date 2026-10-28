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
