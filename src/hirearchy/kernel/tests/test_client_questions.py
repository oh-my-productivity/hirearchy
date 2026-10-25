"""``client_questions``: the items of a result's first "Questions for the client:" block (pure).

The three bodies are the ones study E3 recorded (``studies/E3-org-growth-0a-live/evidence/msgs``), inlined so the test reads no file."""

from __future__ import annotations

import pytest

from hirearchy.kernel import client_questions

# msgs/inbox/20261021T154126566609-lead-1d4c.md: the block opens the summary, three list items
E3_LEAD_1D4C = """## Summary
Questions for the client:
- Lee's Due: "probably by end of next week" resolved to Fri 2026-10-30 (C10; reviewer: Sun 2026-11-01 is the alternative).
- Sam's Due: "during that first week" resolved to 2026-10-30 (C10; reviewer: ambiguous).
- Marta "keep the agenda as sent" has Due none (informal commitment, no date in the notes).

Deliverable: lead/writer/work/memo-2026-10-19.md. I read it myself: 125 words, "Summary:" line first.
Please copy it to /tmp/hirearchy-e3-1792595952/deliverables/memo-2026-10-19.md.

## Lessons
One rework needed: writer resolved "end of next week" to the wrong date.
"""

# msgs/read/20261021T153201308062-lead-1a74.md: the block closes the summary, two list items
E3_LEAD_1A74 = """## Summary
Deliverable: lead/writer/work/memo-2026-10-12.md (126 words per my read).
- C10 met: Due values are 2026-10-14, 2026-10-16, 2026-10-20, 2026-10-21 and none.
Regression R1: its two items (Sam's CI fix and Marta's room) are not in these notes.

Questions for the client:
- Lee's pager swap is Due none (C10). The reviewer notes the notes only say "demo week" (week of 19 Oct), not a single date.
- My own observation: Priya's row says "Implement rate limiter behind feature flag" due 2026-10-20. Do you want it worded "Start implementing"?

## Lessons
Enumerate commitments from the notes first, then compare.
"""

# msgs/inbox/20261021T154342518435-lead-dac0.md: the answer after the client's rework
E3_LEAD_DAC0 = """## Summary
Memo: lead/writer/work/memo-2026-10-19.md (read: 118 words). It is the final file.
- Client rework applied: the Marta "Keep the agenda as sent" row is removed and Sam's Due is none.
Questions for the client: none.

## Lessons
Rework cycle took 1 writer run and 1 reviewer re-check, with no further rework.
"""


def test_e3_lead_1d4c_has_three_questions() -> None:
    items = client_questions(E3_LEAD_1D4C)
    assert len(items) == 3
    assert items[0].startswith("Lee's Due:") and items[0].endswith("is the alternative).")
    assert items[1].startswith("Sam's Due:") and items[2].startswith('Marta "keep the agenda as sent"')


def test_e3_lead_1a74_has_two_questions() -> None:
    items = client_questions(E3_LEAD_1A74)
    assert len(items) == 2
    assert items[0].startswith("Lee's pager swap is Due none (C10).")
    assert items[1].endswith('Do you want it worded "Start implementing"?')


def test_e3_lead_dac0_says_none() -> None:
    assert client_questions(E3_LEAD_DAC0) == []


def test_an_inline_item_is_one_question() -> None:
    assert client_questions("Questions for the client: Is Marta's row an action item?") == ["Is Marta's row an action item?"]
    assert client_questions("**Questions for the client:** Keep the date?\n\nNext paragraph.") == ["Keep the date?"]


def test_a_heading_with_a_blank_line_before_its_list() -> None:
    body = "Done.\n\n## Questions for the client:\n\n- first?\n* second?\n1. third?\n2) fourth?\n\n- not a question\n"
    assert client_questions(body) == ["first?", "second?", "third?", "fourth?"]


@pytest.mark.parametrize("word", ["none", "no", "n/a", "-", "None.", "NONE", "n/a."])
def test_none_words_give_no_item(word: str) -> None:
    assert client_questions(f"Questions for the client: {word}") == []
    assert client_questions(f"Questions for the client:\n- {word}") == []


@pytest.mark.parametrize("text", ["none; all settled", "No, nothing to ask", "none (all settled)", ";"])
def test_an_inline_none_word_first_gives_no_item(text: str) -> None:
    assert client_questions(f"Questions for the client: {text}") == []


def test_a_list_item_that_only_starts_with_a_none_word_is_a_question() -> None:
    assert client_questions("Questions for the client:\n- No one told Marta: keep her row?") == ["No one told Marta: keep her row?"]


def test_a_bullet_prefixed_marker_with_two_items() -> None:  # DR-15
    assert client_questions("- Questions for the client:\n  - one?\n  - two?\n\nDone.") == ["one?", "two?"]
    assert client_questions("* **Questions for the client:**\n- one?\n- two?") == ["one?", "two?"]


def test_only_the_first_block_counts() -> None:
    body = "Questions for the client:\n- first?\n\nQuestions for the client:\n- later?\n"
    assert client_questions(body) == ["first?"]
    assert client_questions("Questions for the client: none.\n\nQuestions for the client:\n- later?") == []


def test_no_block_no_questions() -> None:
    assert client_questions("") == []
    assert client_questions("## Summary\nAll criteria met.\n- a list\n- of things\n") == []
    assert client_questions("We have questions for the client later.") == []


# D-E6-1, A1: the marker line's tail is no item when list items follow it (a heading) or when it is a parenthesized remark, unless it names a
# criterion id (Deviation 1) or starts with a none word (DR-0a4-8).
E6_762F_TAIL = "Questions for the client: (reviewer flags; I did not settle them, and they touch your answers)"  # s1 #70, 762f's exact line
E6_762F_LIST = (
    "- C5: Lee's 'probably by end of next week' is hedged and could mean 10-30 or 11-01.\n"
    "- C4: Marta's prose commitment to keep the agenda is omitted on your instruction. Should the contract exclude such non-actions?\n"
    "- C5: Sam's pairing is Due none, but a reader might want the end of Jo's first week.\n"
)


@pytest.mark.parametrize("final", ["", "."])
def test_762f_marker_tail_is_no_item_and_the_list_items_are_the_questions(final: str) -> None:
    items = client_questions(f"{E6_762F_TAIL}{final}\n{E6_762F_LIST}\nReviewer's final line: criteria met.")
    assert len(items) == 3 and items[0].startswith("C5: Lee's") and items[1].startswith("C4: Marta's") and items[2].startswith("C5: Sam's")


@pytest.mark.parametrize("final", ["", "."])
def test_a_parenthesized_remark_with_no_list_is_no_item(final: str) -> None:
    assert client_questions(f"{E6_762F_TAIL}{final}") == []
    assert client_questions(f"{E6_762F_TAIL}{final}\n\nNext paragraph.") == []


@pytest.mark.parametrize("gap", ["", "\n", "\n\n"])
def test_a_tail_without_an_id_before_list_items_is_a_heading(gap: str) -> None:
    assert client_questions(f"Questions for the client: reviewer flags, not settled{gap}\n- first?\n- second?") == ["first?", "second?"]
    assert client_questions(f"**Questions for the client:** see below{gap}\n1. first?") == ["first?"]


def test_a_tail_that_names_an_id_before_a_list_is_an_item_before_it() -> None:
    body = "Questions for the client: C4: should non-actions be excluded?\n- Style: 'himself' (reviewer: harmless).\n"
    assert client_questions(body) == ["C4: should non-actions be excluded?", "Style: 'himself' (reviewer: harmless)."]


def test_a_parenthesized_tail_that_names_an_id_is_an_item_with_or_without_a_list() -> None:
    assert client_questions("Questions for the client: (C3: keep Marta's row?)") == ["(C3: keep Marta's row?)"]
    assert client_questions("Questions for the client: (C3: keep Marta's row?)\n- a note\n- another") == ["(C3: keep Marta's row?)", "a note", "another"]
    assert client_questions("Questions for the client: (C4-C6)\n- one?\n- two?") == ["(C4-C6)", "one?", "two?"]


def test_a_tail_followed_only_by_a_none_list_line_stays_an_item() -> None:
    assert client_questions("Questions for the client: keep the date?\n- none") == ["keep the date?"]
    assert client_questions("Questions for the client: (a remark)\n- none") == []  # a remark alone is still no item


def test_a_tail_that_only_starts_with_a_parenthesis_is_one_item() -> None:
    assert client_questions("Questions for the client: (C3) Keep Marta's row?") == ["(C3) Keep Marta's row?"]
    assert client_questions("Questions for the client: (a) keep Sam's row? (b) drop Lee's line (style)") == [
        "(a) keep Sam's row? (b) drop Lee's line (style)"
    ]
    assert client_questions("Questions for the client: (a) keep Sam's row? (b) drop Lee's line (style).") == [
        "(a) keep Sam's row? (b) drop Lee's line (style)."
    ]


def test_a_nested_wrapped_tail_is_no_item() -> None:
    assert client_questions("Questions for the client: (see (b))") == []
    assert client_questions("Questions for the client: (see (b)).") == []


def test_a_tail_ending_in_two_dots_is_not_wrapped() -> None:
    assert client_questions("Questions for the client: (maybe..") == ["(maybe.."]
    assert client_questions("Questions for the client: (see below)..") == ["(see below).."]


def test_a_none_word_tail_naming_an_id_is_no_item() -> None:  # DR-0a4-8: rule 1 yields to the none word of rule 4
    assert client_questions("Questions for the client: None (C3 was settled).") == []
    assert client_questions("Questions for the client: None (C3 was settled).\n- later?") == ["later?"]
