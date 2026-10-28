"""The shape of a one-off case (design section 3): two of root's one-off tasks are of one shape when they went to the same assignee and their titles, their
criteria or the words of their criteria say the same thing. A shape group is a connected set of such tasks (pure)."""

from __future__ import annotations

from fractions import Fraction

from hirearchy.retro._shapes import criteria_key, criteria_tokens, groups, related, title_skeleton
from hirearchy.retro._views import OneOffCase

HALF, SIX_TENTHS = Fraction(1, 2), Fraction("0.6")


def one(case_id: str, title: str, *criteria: str, assignee: str = "lead") -> OneOffCase:
    return OneOffCase(case_id, assignee, title, tuple(criteria))


def test_equal_title_skeletons_with_digit_tokens_dropped_are_one_shape() -> None:
    a = one("M1", "Action list for 2026-11-02", "Every action has an owner")
    b = one("M2", "Action list for 2026-11-09", "Nothing here is alike at all", "Not even one line")
    assert title_skeleton(a.title) == title_skeleton(b.title) == ("action", "list", "for")
    assert related(a, b, SIX_TENTHS) == "title"
    assert related(a, one("M3", "Action list for the board"), SIX_TENTHS) == ""  # "the board" is part of the skeleton
    assert title_skeleton("Week 12 notes #7") == ("week", "notes", "#")  # a symbol alone stays a token, a number does not


def test_equal_criteria_keys_are_one_shape() -> None:
    a = one("M1", "Weekly list", "- At most 3 owners per item", "Every action has a due date by 2026-11-09")
    b = one("M2", "Another thing entirely", "At most 5 owners per item.", "Every action has a due date by 2027-01-30")
    assert criteria_key(a.criteria) == criteria_key(b.criteria)
    assert criteria_key(a.criteria) == ("atmost#ownersperitem", "everyactionhasaduedateby#")  # sorted, digit runs masked
    assert related(a, b, SIX_TENTHS) == "criteria"
    assert related(a, one("M3", "Weekly summary", "At most 5 owners per item"), SIX_TENTHS) == ""


def test_the_key_does_not_depend_on_the_order_or_the_markers_of_the_lines() -> None:
    assert criteria_key(("1. B line", "- [x] A line")) == criteria_key(("A line", "B line")) == ("aline", "bline")


def test_a_jaccard_of_at_least_the_overlap_is_one_shape() -> None:
    a = one("M1", "First", "alpha bravo charlie delta")
    b = one("M2", "Second", "alpha bravo charlie echo")  # 3 of 5 words in common: exactly 0.6
    assert criteria_tokens(a.criteria) == frozenset({"alpha", "bravo", "charlie", "delta"})
    assert related(a, b, SIX_TENTHS) == "overlap" and related(a, b, Fraction("0.7")) == "" and related(a, b, Fraction(1, 2)) == "overlap"


def test_digit_tokens_are_not_part_of_the_token_set() -> None:
    assert criteria_tokens(("at most 3 items by 2026-11-09 q4",)) == frozenset({"at", "most", "items", "by", "q"})


def test_another_assignee_is_never_one_shape() -> None:
    a = one("M1", "Action list", "Every action has an owner")
    b = one("M2", "Action list", "Every action has an owner", assignee="other")
    assert related(a, one("M3", "Action list", "Every action has an owner"), SIX_TENTHS) == "title"
    assert related(a, b, SIX_TENTHS) == "" and groups([a, b], SIX_TENTHS) == ()


def test_an_empty_criteria_key_never_matches() -> None:
    a, b = one("M1", "Notes on the first"), one("M2", "Remarks about the second")
    assert criteria_key(a.criteria) == () == criteria_key(b.criteria)
    assert related(a, b, SIX_TENTHS) == ""
    blank = one("M3", "Third thing", "---", "-")  # lines without a letter or a digit have no key either
    assert criteria_key(blank.criteria) == () and related(a, blank, SIX_TENTHS) == ""


def test_an_empty_title_skeleton_never_matches() -> None:
    a, b = one("M1", "2026-11-02", "One line here"), one("M2", "2026-11-09", "Another line there")
    assert title_skeleton(a.title) == () and related(a, b, SIX_TENTHS) == ""


def test_a_token_set_under_three_never_matches_by_overlap() -> None:
    a, b = one("M1", "First", "alpha bravo"), one("M2", "Second", "bravo alpha")  # the same two words, a different line
    assert criteria_tokens(a.criteria) == criteria_tokens(b.criteria) and criteria_key(a.criteria) != criteria_key(b.criteria)
    assert related(a, b, SIX_TENTHS) == ""
    c, d = one("M3", "Third", "alpha bravo charlie"), one("M4", "Fourth", "charlie bravo alpha")  # three words: the overlap counts
    assert related(c, d, SIX_TENTHS) == "overlap"


def test_a_group_is_a_connected_set() -> None:
    a = one("M1", "Action list for 2026-11-02", "alpha bravo charlie delta")
    b = one("M2", "Action list for 2026-11-09", "Nothing alike one")  # joined to a by its title
    c = one("M3", "Something else", "Nothing alike two")  # joined to b by the overlap of its words, to a by neither
    d = one("M4", "Apart", "Unrelated words only")
    e = one("M5", "Elsewhere", "alpha bravo charlie delta", assignee="other")
    assert related(a, c, SIX_TENTHS) == ""
    found = groups([e, d, c, b, a], Fraction("0.4"))
    assert [(g.head, [x.id for x in g.cases], g.relations) for g in found] == [("M1", ["M1", "M2", "M3"], ("title", "overlap"))]
    assert found[0].assignee == "lead" and groups([a, b, c, d, e], Fraction("0.4")) == found  # the order of the input does not matter


def test_the_groups_are_ordered_by_their_smallest_head_and_a_lone_case_is_no_group() -> None:
    cases = [one("M9", "Brief for 5", "x y z"), one("M2", "Report on 1", "p q r"), one("M7", "Brief for 6", "u v w"), one("M4", "Report on 2", "s t u"), one("M5", "Alone")]
    assert [[c.id for c in g.cases] for g in groups(cases, SIX_TENTHS)] == [["M2", "M4"], ["M7", "M9"]]


def test_shape_overlap_comes_from_the_thresholds() -> None:
    a, b = one("M1", "First", "alpha bravo charlie delta"), one("M2", "Second", "alpha bravo charlie echo")
    assert groups([a, b], SIX_TENTHS)[0].relations == ("overlap",)
    assert groups([a, b], Fraction("0.61")) == ()
    assert groups([a, b], Fraction(1, 2))[0].relations == ("overlap",)
