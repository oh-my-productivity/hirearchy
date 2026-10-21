"""The lines of the digest: one case in one line, and the client's verdicts in a chain."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection import Case, Verdict
from hirearchy.reflection._digest import CLIP_LESSON, CLIP_NOTE, DIGEST_CASES, DIGEST_CHARS, MAX_VERDICTS, case_line, verdict_chain
from hirearchy.reflection.testing import ReflectionWorld, fs_world, memory_world

from ._support import SERVICE, ask, define, deliver, populated

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def verdict(kind: str, note: str = "", n: int = 0) -> Verdict:
    message = Message(id=f"20260101T0000{n:02d}000000-root-{n:04d}", sender="root", to="ceo", type="note", body=note, feedback=kind)
    return Verdict(kind, note, T, "T", n, message)


def case(*, verdicts: list[Verdict] | None = None, lessons: list[str] | None = None, lesson_ids: list[str] | None = None, reworks: int = 0) -> Case:
    task = Message(sender="root", to="ceo", type="task", body="b", title="A long title " * 6)
    return Case(
        id="C1", service="s", owner="ceo", tasks=[task], result=None, state="done", playbook=1, used=2, reworks=reworks, budget=9, runs=4,
        lessons=lessons or [], verdicts=verdicts or [], started=T, finished=T, lesson_ids=lesson_ids or [],
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


# ------------------------------------------------------------------------------ case_line


def test_the_line_names_the_case_its_state_playbook_and_runs() -> None:
    assert case_line(case()) == '- case C1 "A long title A long title A long title…": done, playbook v2, 4 of 9 runs'


def test_reworks_are_counted() -> None:
    assert case_line(case(reworks=2)).endswith(", 4 of 9 runs, 2 rework(s)")


def test_the_verdicts_come_before_the_lessons() -> None:
    line = case_line(case(verdicts=[verdict("accept", "good")], lessons=["Search first."]))
    assert line.endswith('; client feedback: accept "good"; lessons: "Search first."')


def test_lessons_written_after_the_first_reject_are_marked() -> None:
    reject = verdict("reject", "no", 1)
    line = case_line(case(verdicts=[reject], lessons=["Fixed it."], lesson_ids=["99999999T000000000000-ceo-0000"]))
    assert 'lessons (written after the reject: check it against her words): "Fixed it."' in line


def test_lessons_written_before_the_reject_are_not_marked() -> None:
    reject = verdict("reject", "no", 1)
    line = case_line(case(verdicts=[reject], lessons=["Fine."], lesson_ids=["00000000T000000000000-ceo-0000"]))
    assert "written after" not in line and 'lessons: "Fine."' in line


def test_the_earlier_lessons_follow_the_latest_where_there_is_room() -> None:
    line = case_line(case(lessons=["first lesson", "second lesson", "latest lesson"]))
    assert line.endswith('lessons: "latest lesson"; earlier: "first lesson / second lesson"')


def test_the_latest_lesson_is_clipped_at_220_and_leaves_no_room_for_the_earlier_ones() -> None:
    line = case_line(case(lessons=["old lesson", "x" * 400]))
    assert line.endswith(f'lessons: "{"x" * 219}…"') and "earlier:" not in line


def test_earlier_lessons_are_clipped_to_the_room_left() -> None:
    line = case_line(case(lessons=["e" * 300, "l" * 100]))
    assert line.endswith(f'lessons: "{"l" * 100}"; earlier: "{"e" * 119}…"')


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
