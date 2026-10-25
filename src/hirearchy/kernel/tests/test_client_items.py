"""``client_items``: the items of a result's "Questions for the client:" block, split by whether an item names a criterion id (D-E6-1, A2).

The split is decided here and nowhere else: ``questions`` (they name a ``C<k>``) are the ones the client must decide, ``notes`` (they name none) are
shown and never withheld. Together they are every item ``client_questions`` finds, each once, in the block's order."""

from __future__ import annotations

import re

import pytest
from testkit.e6_replay import EV6

from hirearchy.kernel import ClientItems, client_items, client_questions

from .test_client_questions import E3_LEAD_1A74, E3_LEAD_1D4C, E3_LEAD_DAC0, E6_762F_LIST, E6_762F_TAIL

MARKER_LINE = re.compile(r"^\W*questions for the client", re.IGNORECASE | re.MULTILINE)


def e6_results() -> list[tuple[str, str]]:
    """The results with a ``Questions for the client:`` block that root received in E6's three streams (``msgs/read`` and ``msgs/inbox``): the stream
    and the whole file as the body. A missing evidence directory fails the test, never skips it."""
    found: list[tuple[str, str]] = []
    for stream in ("s1", "s2", "s3"):
        if not (EV6 / stream / "msgs").is_dir():
            pytest.fail(f"no evidence directory {EV6 / stream / 'msgs'}")
        for box in ("read", "inbox"):
            for path in sorted((EV6 / stream / "msgs" / box).glob("*.md")) if (EV6 / stream / "msgs" / box).is_dir() else []:
                text = path.read_text(encoding="utf-8")
                if "type: result" in text.split("---")[1] and MARKER_LINE.search(text):
                    found.append((f"{stream}/{path.name}", text))
    return found


def e6_body(name: str) -> str:
    """The recorded result whose id ends in ``name`` (``8613``)."""
    (text,) = [t for n, t in e6_results() if n.endswith(f"-lead-{name}.md")]
    return text


@pytest.mark.parametrize(
    "item",
    ["C3/C4: keep the row?", "(C5; reviewer: ambiguous)", "Which Friday? AMB1 (C5)", "Criterion: C4.", "C12 is unclear", "C3: Keep Marta's row?"],
)
def test_an_item_that_names_a_criterion_id_is_a_question(item: str) -> None:
    assert client_items(f"Questions for the client:\n- {item}\n") == ClientItems((item,), ())


@pytest.mark.parametrize("item", ["CI is red", "c5 is lower case", "C2C is not an id", "ABC1 is not an id", "Style: 'himself' (reviewer: harmless).", "C is a letter"])
def test_an_item_that_names_none_is_a_note(item: str) -> None:
    assert client_items(f"Questions for the client:\n- {item}\n") == ClientItems((), (item,))


def test_each_part_keeps_the_order_of_the_block() -> None:
    body = "Questions for the client:\n- note a\n- C2: q two?\n- note b\n- C1: q one?\n- note c\n"
    assert client_items(body) == ClientItems(("C2: q two?", "C1: q one?"), ("note a", "note b", "note c"))


def test_an_empty_body_and_a_block_that_says_none_give_nothing() -> None:
    assert client_items("") == ClientItems((), ())
    assert client_items("Questions for the client: none.") == ClientItems()
    assert client_items(E3_LEAD_DAC0) == ClientItems()
    assert client_items("no block at all") == ClientItems()


def test_the_default_client_items_is_empty() -> None:
    assert ClientItems() == ClientItems((), ())


def test_an_id_tagged_tail_before_a_notes_only_list_is_one_question_and_the_notes() -> None:
    body = "Questions for the client: C4: should non-actions be excluded?\n- Style: 'himself' (reviewer: harmless).\n- Typo in row 2.\n"
    assert client_items(body) == ClientItems(("C4: should non-actions be excluded?",), ("Style: 'himself' (reviewer: harmless).", "Typo in row 2."))


def test_the_split_of_762f_has_three_questions_and_no_note() -> None:
    got = client_items(f"{E6_762F_TAIL}\n{E6_762F_LIST}")
    assert len(got.questions) == 3 and got.notes == ()


def test_client_items_is_the_class_of_a_frozen_pair() -> None:
    got = client_items("Questions for the client:\n- C1: q?\n")
    with pytest.raises(AttributeError):
        got.questions = ()  # type: ignore[misc]


def check_split(body: str) -> None:
    items = client_questions(body)
    got = client_items(body)
    assert len(got.questions) + len(got.notes) == len(items)  # every item once
    assert sorted(got.questions + got.notes) == sorted(items)
    assert list(got.questions) == [i for i in items if re.search(r"\bC[0-9]+\b", i)]  # exhaustive and disjoint, in the block's order
    assert list(got.notes) == [i for i in items if not re.search(r"\bC[0-9]+\b", i)]


@pytest.mark.parametrize("body", [E3_LEAD_1D4C, E3_LEAD_1A74, E3_LEAD_DAC0, f"{E6_762F_TAIL}\n{E6_762F_LIST}"])
def test_the_parts_are_every_item_of_the_block_once_for_the_existing_bodies(body: str) -> None:
    check_split(body)


def test_the_parts_are_every_item_of_the_block_once_for_every_e6_result() -> None:
    results = e6_results()
    assert len(results) == 19
    for _, body in results:
        check_split(body)


@pytest.mark.parametrize(("name", "questions", "notes"), [("8613", 2, 1), ("762f", 3, 0), ("6c63", 0, 1), ("d80f", 2, 0)])
def test_the_four_results_the_replays_name(name: str, questions: int, notes: int) -> None:
    got = client_items(e6_body(name))
    assert (len(got.questions), len(got.notes)) == (questions, notes)


def test_8613s_note_is_the_style_item_and_6c63s_is_the_section_item() -> None:
    assert client_items(e6_body("8613")).notes == ("Style: 'himself' in Sam's table row (reviewer: harmless).",)
    (note,) = client_items(e6_body("6c63")).notes
    assert note.startswith("Keep or delete the '## Open, not decided' section")


def test_the_nineteen_results_of_e6_hold_49_items_47_questions_and_2_notes() -> None:
    parts = [client_items(body) for _, body in e6_results()]
    assert (sum(len(p.questions) + len(p.notes) for p in parts), sum(len(p.questions) for p in parts), sum(len(p.notes) for p in parts)) == (49, 47, 2)
