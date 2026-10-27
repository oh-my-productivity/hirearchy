"""The lines of the digest: one case in one line, and the client's verdicts in a chain."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection import Case, Verdict
from hirearchy.reflection._digest import CLIP_LESSON, CLIP_NOTE, DIGEST_CASES, DIGEST_CHARS, MAX_VERDICTS, AarParts, aar_parts, case_line, verdict_chain
from hirearchy.reflection.testing import ReflectionWorld, fs_world, memory_world

from ._support import SERVICE, ask, define, deliver, populated

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def verdict(kind: str, note: str = "", n: int = 0, tier: str = "human") -> Verdict:
    message = Message(id=f"20260101T0000{n:02d}000000-root-{n:04d}", sender="root", to="ceo", type="note", body=note, feedback=kind)
    return Verdict(kind, note, T, "T", n, message, tier=tier)


def case(
    *, verdicts: list[Verdict] | None = None, lessons: list[str] | None = None, lesson_ids: list[str] | None = None, reworks: int = 0,
    relayed: int = 0, client_kind: str = "human", lesson_sources: list[str] | None = None,
) -> Case:
    task = Message(sender="root", to="ceo", type="task", body="b", title="A long title " * 6)
    return Case(
        id="C1", service="s", owner="ceo", tasks=[task], result=None, state="done", playbook=1, used=2, reworks=reworks, budget=9, runs=4,
        lessons=lessons or [], verdicts=verdicts or [], started=T, finished=T, lesson_ids=lesson_ids or [], client_kind=client_kind,
        relayed_reworks=relayed, lesson_sources=lesson_sources or [],
    )


def test_the_constants_of_the_digest() -> None:
    assert (CLIP_LESSON, CLIP_NOTE, MAX_VERDICTS) == (220, 160, 4)
    assert (DIGEST_CASES, DIGEST_CHARS) == (6, 3000)


# ------------------------------------------------------------------------------ verdict_chain


def test_a_bare_accept_has_no_quotes() -> None:
    assert verdict_chain(case(verdicts=[verdict("accept")])) == "accept"


def test_each_verdict_has_her_words() -> None:
    assert verdict_chain(case(verdicts=[verdict("reject", "too long", 1), verdict("accept", "this one is right", 2)])) == (
        'reject "too long" -> accept "this one is right"'
    )


def test_the_words_of_two_verdicts_are_clipped_at_160_characters_each() -> None:
    long = "w" * 300
    chain = verdict_chain(case(verdicts=[verdict("reject", long, 1), verdict("reject", long, 2)]))
    assert chain == " -> ".join([f'reject "{"w" * 159}…"'] * 2)


def test_the_words_of_three_or_more_verdicts_are_clipped_at_80_characters_each() -> None:
    long = "w" * 300
    chain = verdict_chain(case(verdicts=[verdict("reject", long, n) for n in (1, 2, 3)]))
    assert chain == " -> ".join([f'reject "{"w" * 79}…"'] * 3)


def test_only_the_latest_four_verdicts_are_shown_after_an_ellipsis() -> None:
    chain = verdict_chain(case(verdicts=[verdict("reject", f"problem {i}", i) for i in range(6)]))
    assert chain == '… -> reject "problem 2" -> reject "problem 3" -> reject "problem 4" -> reject "problem 5"'


def test_four_verdicts_are_shown_whole() -> None:
    assert not verdict_chain(case(verdicts=[verdict("reject", f"p{i}", i) for i in range(4)])).startswith("…")


def test_verdict_chain_without_a_mapping_is_unchanged() -> None:
    human = case(verdicts=[verdict("reject", "too long", 1), verdict("accept", "this one is right", 2)])
    assert verdict_chain(human) == verdict_chain(human, None) == 'reject "too long" -> accept "this one is right"'
    assert verdict_chain(human, {}) == verdict_chain(human)  # a verdict the mapping does not know keeps no id


def test_the_digest_names_human_rejections_by_r_id() -> None:
    c = case(verdicts=[verdict("reject", "too long", 1), verdict("reject", "wrong week", 2), verdict("accept", "ok", 3)])
    ids = {c.verdicts[0].message.id: "R1", c.verdicts[1].message.id: "R4"}
    assert verdict_chain(c, ids) == 'reject R1 "too long" -> reject R4 "wrong week" -> accept "ok"'


def test_the_digest_labels_relayed_verdicts() -> None:
    c = case(verdicts=[verdict("reject", "long?", 1, "relayed"), verdict("accept", "", 2, "relayed")])
    assert verdict_chain(c) == 'reject (relayed) "long?" -> accept (relayed)'
    ids = {c.verdicts[0].message.id: "R1"}  # a relayed verdict is no assertion: it never gets an id
    assert verdict_chain(c, ids) == verdict_chain(c)


def test_the_digest_labels_an_agent_clients_feedback() -> None:
    c = case(verdicts=[verdict("reject", "thin", 1, "agent")], client_kind="agent")
    assert case_line(c).endswith('; client feedback (an agent client: hypotheses): reject "thin"')
    assert "; client feedback: " in case_line(case(verdicts=[verdict("reject", "thin", 1)]))


# ------------------------------------------------------------------------------ case_line


def test_the_line_names_the_case_its_state_playbook_and_runs() -> None:
    assert case_line(case()) == '- case C1 "A long title A long title A long title…": done, playbook v2, 4 of 9 runs'


def test_reworks_are_counted() -> None:
    assert case_line(case(reworks=2)).endswith(", 4 of 9 runs, 2 rework(s)")


def test_the_case_line_counts_relayed_reworks() -> None:
    assert case_line(case(reworks=3, relayed=2)).endswith(", 4 of 9 runs, 3 rework(s), 2 relayed")
    assert case_line(case(reworks=2)).endswith(", 2 rework(s)")  # none relayed: the part is unchanged


def test_the_case_line_names_the_assertions_it_is_given() -> None:
    c = case(verdicts=[verdict("reject", "no", 1)])
    assert case_line(c, {c.verdicts[0].message.id: "R2"}).endswith('; client feedback: reject R2 "no"')


def test_the_verdicts_come_before_the_lessons() -> None:
    line = case_line(case(verdicts=[verdict("reject", "too long")], lessons=["Search first."]))
    assert line.endswith('; client feedback: reject "too long"; owner\'s view: "Search first."')


def test_lessons_written_after_the_first_reject_are_marked() -> None:
    reject = verdict("reject", "no", 1)
    line = case_line(case(verdicts=[reject], lessons=["Fixed it."], lesson_ids=["99999999T000000000000-ceo-0000"]))
    assert 'owner\'s view (written after the reject: check it against her words): "Fixed it."' in line


def test_lessons_written_before_the_reject_are_not_marked() -> None:
    reject = verdict("reject", "no", 1)
    line = case_line(case(verdicts=[reject], lessons=["Fine."], lesson_ids=["00000000T000000000000-ceo-0000"]))
    assert "written after" not in line and 'owner\'s view: "Fine."' in line


def test_the_earlier_lessons_follow_the_latest_where_there_is_room() -> None:
    line = case_line(case(lessons=["first lesson", "second lesson", "latest lesson"]))
    assert line.endswith('owner\'s view: "latest lesson"; earlier: "first lesson / second lesson"')


def test_the_latest_lesson_is_clipped_at_220_and_leaves_no_room_for_the_earlier_ones() -> None:
    line = case_line(case(lessons=["old lesson", "x" * 400]))
    assert line.endswith(f'owner\'s view: "{"x" * 219}…"') and "earlier:" not in line


def test_earlier_lessons_are_clipped_to_the_room_left() -> None:
    line = case_line(case(lessons=["e" * 300, "l" * 100]))
    assert line.endswith(f'owner\'s view: "{"l" * 100}"; earlier: "{"e" * 119}…"')


def test_a_single_lesson_has_no_earlier_part() -> None:
    assert "earlier:" not in case_line(case(lessons=["Only one."]))


# ------------------------------------------------------------------------------ moved from tests/test_round_f_runtime.py (assertions unchanged)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    world = populated(request.param(tmp_path))
    define(world)
    return world


def test_case_line_drops_earlier_lessons_when_there_is_no_room_and_never_clips_the_latest_first(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task, lessons="Only one.")
    case = w.history.cases("ceo", SERVICE)[0]
    assert "earlier:" not in case_line(case)
    case.lessons = ["old lesson", "x" * 400]
    line = case_line(case)
    assert "earlier:" not in line and "old lesson" not in line and "x" * 100 in line


# ------------------------------------------------------------------------------ lessons of relayed reworks (4.4)

RELAYED = "from a relayed rework, not the client's"


def test_the_latest_lesson_of_a_relayed_rework_is_marked() -> None:
    line = case_line(case(lessons=["first", "second"], lesson_ids=["r1", "r2"], lesson_sources=["", "relayed"]))
    assert f'; owner\'s view ({RELAYED}): "second"' in line


def test_both_marks_are_joined_when_written_after_the_reject() -> None:
    reject = verdict("reject", "too long", 1)
    line = case_line(case(verdicts=[reject], lessons=["x"], lesson_ids=["20260101T000009000000-ceo-0001"], lesson_sources=["relayed"]))
    assert f'; owner\'s view ({RELAYED}; written after the reject: check it against her words): "x"' in line


def test_earlier_relayed_lessons_are_prefixed() -> None:
    line = case_line(case(lessons=["a", "b", "c"], lesson_ids=["r1", "r2", "r3"], lesson_sources=["relayed", "human", "relayed"]))
    assert '; earlier: "(relayed) a / b"' in line and f'owner\'s view ({RELAYED}): "c"' in line


def test_human_and_unsourced_lessons_are_unmarked() -> None:
    for sources in (["", "human"], ["human", "human"], []):
        line = case_line(case(lessons=["a", "b"], lesson_ids=["r1", "r2"], lesson_sources=sources))
        assert "relayed" not in line and '; owner\'s view: "b"; earlier: "a"' in line


# ------------------------------------------------------------------------------ lessons as after-action reviews, the owner's view (design 11)

FULL = "Expected: C6. Happened: the date was missing. Caught at: the check step. Cause: no step reads the date. Prevent: add a date check."


def test_aar_parts_reads_the_five_labels_case_insensitively_after_a_sentence_end() -> None:
    assert aar_parts(FULL) == AarParts("C6", "the date was missing", "the check step", "no step reads the date", "add a date check", "")
    assert aar_parts("expected: C6; HAPPENED: late\nCAUGHT AT: review\n cause: input. prevent: a check.") == AarParts(
        "C6", "late", "review", "input", "a check", ""
    )
    assert aar_parts("Near miss: the link almost broke.") == AarParts(near_miss="the link almost broke")
    assert aar_parts("The cause: unknown. Expected: C1") == AarParts(expected="C1") and aar_parts("Why it happened: x") is None  # not at a sentence start
    assert aar_parts("Clean run; no issues.") is None and aar_parts("") is None
    assert aar_parts("Prevent regressions. Cause analysis later.") is None  # a label needs its colon


def test_a_part_runs_to_the_next_label_and_the_first_of_a_repeated_label_wins() -> None:
    parts = aar_parts("Expected: C6 and C7. Cause: a hand-off; Cause: another. Prevent: a check.")
    assert parts == AarParts(expected="C6 and C7", cause="a hand-off", prevent="a check")


def test_a_lesson_with_labels_reads_owners_view_as_parts() -> None:
    assert case_line(case(lessons=[FULL])).endswith(
        "; owner's view: Expected C6 | Happened the date was missing | Caught at the check step | Cause no step reads the date | Prevent add a date check"
    )


def test_a_lesson_without_labels_reads_owners_view_quoted() -> None:
    assert case_line(case(lessons=["Search first."])).endswith('; owner\'s view: "Search first."')
    assert "lessons" not in case_line(case(lessons=["Search first."]))


def test_an_accepted_case_shows_its_near_miss_or_none_recorded() -> None:
    accept = verdict("accept", "good", 1)
    assert case_line(case(verdicts=[accept], lessons=["Near miss: the date was nearly wrong. Prevent: x."])).endswith("; owner's view: near miss: the date was nearly wrong")
    assert case_line(case(verdicts=[accept], lessons=["Search first."])).endswith("; owner's view: near miss: none recorded")
    assert case_line(case(verdicts=[accept], lessons=[FULL])).endswith("; owner's view: near miss: none recorded")  # a failure review of an accepted case
    assert case_line(case(verdicts=[accept], lessons=["Near miss: none."])).endswith("; owner's view: near miss: none")
    reject_then_accept = [verdict("reject", "no", 1), verdict("accept", "now fine", 2)]
    assert "near miss: none recorded" in case_line(case(verdicts=reject_then_accept, lessons=["Search first."]))
    assert "near miss" not in case_line(case(verdicts=[verdict("reject", "no", 1)], lessons=["Near miss: x."]))  # a rejected case shows its review
    assert "owner's view" not in case_line(case(verdicts=[accept]))  # no lesson, no view


def test_the_relayed_and_after_reject_marks_stay_inside_the_tag() -> None:
    reject = verdict("reject", "too long", 1)
    both = case_line(case(verdicts=[reject], lessons=[FULL], lesson_ids=["20260101T000009000000-ceo-0001"], lesson_sources=["relayed"]))
    assert f"; owner's view ({RELAYED}; written after the reject: check it against her words): Expected C6 | Happened " in both
    assert case_line(case(lessons=["a", "b"], lesson_ids=["r1", "r2"], lesson_sources=["", "relayed"])).count(f"owner's view ({RELAYED}): ") == 1
    accepted = [verdict("reject", "no", 1), verdict("accept", "ok", 2)]
    line = case_line(case(verdicts=accepted, lessons=["x"], lesson_ids=["20260101T000009000000-ceo-0001"], lesson_sources=["relayed"]))
    assert f"; owner's view ({RELAYED}; written after the reject: check it against her words): near miss: none recorded" in line


def test_each_part_is_clipped_to_60_and_the_line_to_220() -> None:
    long = "w" * 100
    line = case_line(case(lessons=[f"Expected: {long}. Happened: short."]))
    assert line.endswith(f"; owner's view: Expected {'w' * 59}… | Happened short")
    five = case_line(case(lessons=[f"Expected: {long}. Happened: {long}. Caught at: {long}. Cause: {long}. Prevent: {long}."]))
    view = five.split("; owner's view: ")[1]
    assert len(view) == CLIP_LESSON and view.endswith("…") and view.startswith(f"Expected {'w' * 59}… | Happened ")
    near = case_line(case(verdicts=[verdict("accept", "ok", 1)], lessons=[f"Near miss: {long}."]))
    assert near.endswith(f"near miss: {'w' * 59}…")


def test_the_earlier_lessons_follow_an_after_action_view_where_there_is_room() -> None:
    line = case_line(case(lessons=["first lesson", "Expected: C1. Prevent: a check."]))
    assert line.endswith('; owner\'s view: Expected C1 | Prevent a check; earlier: "first lesson"')


def test_an_admission_and_a_watch_are_equal_with_and_without_a_lesson(tmp_path: Path) -> None:
    """The gate and the watch read no lesson text (design 11, "never evidence"): the same story with any lessons gives the same answers."""
    from ._support import note_on

    def run(lessons: str, where: Path) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], object]:
        where.mkdir()
        world = populated(fs_world(where))
        define(world)
        for topic in ("a", "b"):  # criterion C2 failed in two cases the client rejected (rule (b))
            task = ask(world, topic)
            deliver(world, task, lessons=lessons)
            no = note_on(world, task, verdict="reject", source="human", body="No source.")
            note_on(world, task, reply_to=no.id, source="human", criterion="C2")
        admitted = world.evidence.admit_item("ceo", SERVICE, ["C2"], "why", kind="step", text="Cite every claim.", when=None)
        return (admitted.rule, admitted.evidence, tuple(sorted(admitted.why))), world.evidence.watch("ceo", SERVICE)

    plain = run("Clean run; no issues.", tmp_path / "plain")
    review = run(FULL, tmp_path / "review")
    assert plain == review and plain[0][0] == "b"
