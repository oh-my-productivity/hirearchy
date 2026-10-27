"""The pure rules of ``revise_playbook`` (design 7, 9.1, 10): the 30% rule, the cap's two lists and the weakening rule. No file, no world."""

from __future__ import annotations

import pytest

from hirearchy.kernel import OrgError
from hirearchy.services import ItemWatch, PlaybookItem
from hirearchy.services._ops import (
    PB_SPLIT, CapCandidate, cap_lists, cap_refusal, content_tokens, split_check, split_limit, weakening,
)


def words(n: int, prefix: str = "w") -> list[str]:
    return [f"{prefix}{i}" for i in range(n)]


def step(n: int, text: str = "text", why: tuple[str, ...] = ()) -> PlaybookItem:
    return PlaybookItem(f"P{n}", "step", "## Steps", text, why=why)


def watch(n: int, state: str = "kept", since: int = 1, coverage: tuple[str, ...] = (), carried: str = "") -> ItemWatch:
    return ItemWatch(f"P{n}", "step", state, since, coverage=coverage, carried=carried)


# ------------------------------------------------------------------------------ the 30% rule (7)


def test_content_tokens_are_the_tokens_of_texts_whens_and_headings_never_markers_why_or_ids() -> None:
    items = (
        PlaybookItem("P1", "step", "## Steps", "Read the **request**.", why=("R1", "C2")),
        PlaybookItem("P2", "rule", "## Rules", "cite it", "a claim has no source", ("R1",)),
        PlaybookItem("P3", "rule", "## Rules", "always cite", "always"),
    )
    assert sorted(content_tokens(items, ["## Steps", "## Rules"])) == sorted(
        ["steps", "rules", "read", "the", "request", "a", "claim", "has", "no", "source", "cite", "it", "always", "cite"],
    )  # the headings and the words; "always" as a when counts none, and no marker, WHY or id is a token


def test_split_limit_is_the_max_of_30_percent_rounded_up_and_50_words() -> None:
    assert [split_limit(n) for n in (0, 1, 100, 166, 167, 168, 400, 401, 1000)] == [50, 50, 50, 50, 51, 51, 120, 121, 300]


def test_split_check_refuses_above_the_max_of_30_percent_and_50_words() -> None:
    current = words(400)  # the limit is 120
    split_check(current, [*current, *words(120, "n")])  # 120 words added: at the limit
    with pytest.raises(OrgError, match=r"touches 121 of the playbook's 400 words"):
        split_check(current, [*current, *words(121, "n")])
    split_check(current, [*words(60, "n"), *current[60:]])  # 60 replaced = 60 gone + 60 new = 120
    with pytest.raises(OrgError, match=r"touches 122 of the playbook's 400 words"):
        split_check(current, [*words(61, "n"), *current[61:]])
    with pytest.raises(OrgError, match=r"touches 121 of the playbook's 400 words"):
        split_check(current, current[:279])  # 121 words gone


def test_the_floor_of_50_words_lets_a_small_playbook_take_an_ordinary_rule() -> None:
    current = words(100)  # 30% of 100 is 30: the floor of 50 applies
    split_check(current, [*current, *words(50, "n")])
    with pytest.raises(OrgError, match=r"touches 51 of the playbook's 100 words, more than about 30% \(50\)"):
        split_check(current, [*current, *words(51, "n")])


def test_base_0_uses_the_50_word_floor() -> None:
    split_check([], words(50))  # the first item of an empty playbook is an ordinary add
    with pytest.raises(OrgError, match=r"touches 51 of the playbook's 0 words, more than about 30% \(50\)"):
        split_check([], words(51))


def test_a_reordering_or_a_formatting_change_touches_no_word() -> None:
    current = words(300)
    split_check(current, list(reversed(current)))  # a multiset: the order is none of its business
    split_check(current, current)


def test_pb_split_word_for_word() -> None:
    with pytest.raises(OrgError) as e:
        split_check(words(100), words(160, "n"))
    assert str(e.value) == (
        "refused: this change touches 260 of the playbook's 100 words, more than about 30% (50): make it as smaller changes (one item, or part of an "
        "item, per call), each with its own reason and evidence, so each one is judged and watched on its own. Nothing was written."
    )
    assert PB_SPLIT.format(changed=1, base=2, limit=3).startswith("refused: this change touches 1 of the playbook's 2 words, more than about 30% (3)")


# ------------------------------------------------------------------------------ the cap's candidates (10)


def test_the_candidates_are_new_items_whose_watch_rests_on_no_r_id() -> None:
    items = [step(1), step(2), step(3), step(4)]
    watches = {w.id: w for w in (watch(1, "kept"), watch(2, "new", 4, ("C9",)), watch(3, "new", 5), watch(4, "warning", 3))}
    started = {"P2": ("C9",), "P3": ("R1", "C2"), "P4": ("C2",)}  # the why of the change that started each item's watch
    candidates, _ = cap_lists(items, watches, started)
    assert candidates == [CapCandidate("P2", 4, ("C9",))]  # P3 rests on an R id; P4 is warned (no longer new); P1 is kept


def test_carried_and_w2_restored_watches_are_no_candidates() -> None:
    """R3-F6: a repaired item that carries a watch has its own watch, and an item whose owner restored a client-written text has no why entry
    of its own: the cap must not cut either short."""
    items = [step(1), step(2), step(3)]
    watches = {w.id: w for w in (watch(1, "new", 2), watch(2, "new", 3, carried="P9"), watch(3, "new", 4))}
    started = {"P1": ("C2",), "P2": ("C2",)}  # P3 has no entry: its watch was started by an exempt restore
    candidates, _ = cap_lists(items, watches, started)
    assert [c.id for c in candidates] == ["P1"]


def test_candidates_are_ordered_by_live_from_and_at_most_5() -> None:
    items = [step(n) for n in range(1, 9)]
    watches = {f"P{n}": watch(n, "new", since=10 - n, coverage=("C1",) if n % 2 else ()) for n in range(1, 9)}
    started = {f"P{n}": ("C1",) for n in range(1, 9)}
    candidates, _ = cap_lists(items, watches, started)
    assert [(c.id, c.since) for c in candidates] == [("P8", 2), ("P7", 3), ("P6", 4), ("P5", 5), ("P4", 6)]


def test_the_second_list_is_the_oldest_uncovered_items_at_most_5() -> None:
    items = [step(n) for n in range(1, 9)]
    watches = {f"P{n}": watch(n, "kept", since=n % 4 + 1, coverage=("C1",) if n == 2 else ()) for n in range(1, 9)}
    _, uncovered = cap_lists(items, watches, {})
    # P2 covers a criterion; of the other seven the oldest five by (since, number): P4 and P8 (v1), P1 and P5 (v2), P6 (v3); P3 and P7 (v4) are cut
    assert uncovered == [("P4", 1), ("P8", 1), ("P1", 2), ("P5", 2), ("P6", 3)]


def test_an_item_the_watch_does_not_know_counts_as_uncovered_since_the_current_version() -> None:
    _, uncovered = cap_lists([step(1)], {}, {}, current=7)
    assert uncovered == [("P1", 7)]


# ------------------------------------------------------------------------------ PB-CAP


def test_pb_cap_word_for_word() -> None:
    candidates = [CapCandidate("P7", 4, ("C9",)), CapCandidate("P8", 5, ())]
    uncovered = [("P4", 1), ("P5", 2)]
    assert cap_refusal(1012, 1000, candidates, uncovered, "root") == (
        "refused: the playbook would have 1012 words; the limit is 1000 (playbook_max_words). Retire an item first. Candidates, oldest first (new "
        "items whose watch rests on no regression assertion): P7 (since v4; cites C9: retiring it needs root's acknowledgement), P8 (since v5). "
        "Items that cover no criterion or assertion (no acknowledgement needed): P4 (since v1), P5 (since v2). "
        'Or shorten an item (op="edit"). Nothing was written.'
    )
    assert cap_refusal(1012, 1000, [], uncovered, "ceo").startswith("refused: the playbook would have 1012 words; the limit is 1000 (playbook_max_words). Retire an item first. Items that cover")


def test_both_cap_lists_empty_say_retire_one_yourself() -> None:
    assert cap_refusal(1001, 1000, [], [], "root") == (
        "refused: the playbook would have 1001 words; the limit is 1000 (playbook_max_words). Retire an item first. Every item covers a criterion or an "
        "assertion: retire one yourself (it needs root's acknowledgement), or shorten one. Nothing was written."
    )


# ------------------------------------------------------------------------------ the weakening rule (9.1)


def item(text: str, when: str = "", kind: str = "step") -> PlaybookItem:
    return PlaybookItem("P1", kind, "## Steps", text, when)


def test_weakening_by_a_dropped_covered_id_or_a_strict_sub_multiset_of_words() -> None:
    old = item("Cite every claim with its source URL")
    # (i) the new text's coverage lacks an id of the old text's coverage
    assert weakening(old, item("Cite every claim with its source link"), ("C2",), ()) is True
    assert weakening(old, item("Cite every claim with its source link"), ("C2", "R1"), ("R1",)) is True
    assert weakening(old, item("Cite every claim with its source link"), ("C2",), ("C2", "C3")) is False
    # (ii) the new text's content words are a strict sub-multiset of the old text's: it only deletes words
    assert weakening(old, item("Cite every claim"), (), ()) is True
    assert weakening(old, item("Cite every claim with its source URL and a date"), (), ()) is False
    assert weakening(old, item("Cite every source"), (), ()) is True
    assert weakening(old, item("Cite every claim twice"), (), ()) is False  # one word added: not a sub-multiset


def test_a_rules_when_counts_in_its_content_words() -> None:
    old = item("cite it", "a claim has no source", "rule")
    assert weakening(old, item("cite it", "a claim has none", "rule"), (), ()) is False
    assert weakening(old, item("cite it", "a claim has", "rule"), (), ()) is True
    assert weakening(old, item("cite it", "always", "rule"), (), ()) is True


def test_a_formatting_fix_is_never_weakening() -> None:
    old = item("Cite **every** claim.")
    assert weakening(old, item("cite every claim"), ("C2", "R1"), ()) is False  # equal tokens: the coverage is the old one's anyway
    assert weakening(old, item("Cite every claim"), ("C2",), ("C2",)) is False


def test_a_restore_of_a_retired_item_is_never_weakening() -> None:
    assert weakening(None, item("Cite every claim"), ("C2",), ()) is False
