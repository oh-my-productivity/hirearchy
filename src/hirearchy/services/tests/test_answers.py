"""``repeats_rejection``: do the words offered as the user's answer repeat the rejection they answer? (P2-WORDS-ARE-THE-REJECTION)

The four cases of the recorded evidence (E4 and E3, read from the repository) decide the rule: a paste of the reject turn is caught, the user's real
yes is not."""

from __future__ import annotations

import json
import re

import pytest
import testkit

from hirearchy.services import repeats_rejection

E4 = testkit.REPO / "studies" / "E4-org-growth-0a1-recheck" / "evidence"
E3 = testkit.REPO / "studies" / "E3-org-growth-0a-live" / "evidence"


def e4_note(stream: str, call: int) -> str:
    """The ``note`` argument of call ``#call`` in the contract loop of an E4 stream (a missing file or call fails the test)."""
    lines = (E4 / stream / "contract-loop.txt").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\[[^\]]+\] call #{call} ", line))
    return str(json.loads(lines[start + 1].removeprefix("ARGS: "))["arguments"]["note"])


def e3_note(call: int) -> str:
    """The ``note`` argument of ``CALL #call`` in E3's tool-call log."""
    line = next(x for x in (E3 / "assistant-tool-calls.txt").read_text(encoding="utf-8").splitlines() if f"CALL #{call} " in x)
    return str(json.loads(line.split("args=", 1)[1])["arguments"]["note"])


def test_repeats_rejection_on_the_four_evidence_cases() -> None:
    s1r_t5 = (E4 / "s1r" / "turn-05.prompt.txt").read_text(encoding="utf-8").strip()
    rejection = e4_note("s1r", 22)  # the rejection root recorded 0.46 s before the amendment
    assert repeats_rejection(s1r_t5, rejection) is True  # Lena's turn 5 is the rejection with "No, not right yet." before it
    e3_lines = (E3 / "turn-05.txt").read_text(encoding="utf-8").splitlines()
    e3_t5 = e3_lines[e3_lines.index("######## LENA (prompt sent verbatim):") + 1]  # Lena's line in E3's turn 5
    assert repeats_rejection(e3_t5, e3_note(24)) is True  # E3: the very same words
    assert repeats_rejection("Yes, add it.", rejection) is False  # the user's answer to the question
    assert repeats_rejection(e4_note("s1r", 23), rejection) is False  # "Yes, add it. Yes, fund it - but please keep an eye on the cost."


def test_the_evidence_notes_are_what_the_tests_assume() -> None:
    assert e4_note("s1r", 22).startswith("Sam's CI item says 'before Friday'")
    assert e3_note(24).startswith("No, not right yet. Sam's CI item")


def test_repeats_rejection_is_symmetric_and_needs_four_words_for_a_run() -> None:
    note = "Sam's CI item says before Friday so it has a date."
    assert repeats_rejection(note, note) and repeats_rejection(note.upper(), note) and repeats_rejection(" " + note + "!!", note)
    assert repeats_rejection("No, not right yet. " + note + " And more.", note) is True  # the note inside a longer paste
    assert repeats_rejection("Sam's CI item says", note) is True  # a part of the note (4 words) inside the note
    assert repeats_rejection(note, "No, not right yet. " + note + " And more.") is True  # symmetric
    assert repeats_rejection("Sam's CI says item", note) is False  # not a contiguous run
    assert repeats_rejection("item says before", note) is False  # a contiguous run of three words: too few
    assert repeats_rejection("", note) is False and repeats_rejection(note, "") is False


@pytest.mark.parametrize("words, note, expected", [
    ("Yes", "Yes", True), ("yes!", "YES", True),  # fewer than four words: equality only
    ("Yes, add it.", "No. Yes, add it.", False),  # three words inside a longer text: not a repeat
    ("yes add it", "Yes, add it", True),
    ("no", "yes", False),
])
def test_repeats_rejection_with_fewer_than_four_words_needs_equality(words: str, note: str, expected: bool) -> None:
    assert repeats_rejection(words, note) is expected
