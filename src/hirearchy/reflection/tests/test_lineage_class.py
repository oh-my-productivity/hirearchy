"""The lineage class of a criterion (design 3, 10.5, PC-2): the criterion and what the answers that added its text replaced, as of a time."""

from __future__ import annotations

from hirearchy.reflection import lineage_class

from ._watch_kit import contract, stamp

NINE = ["w", "x", "y", "z", "u", "v", "q", "r", "s"]  # C1-C9: "v" is C6
TEN = [*NINE[:5], "ten", *NINE[6:]]  # C6 replaced by C10
ELEVEN = [*NINE[:5], "eleven", *NINE[6:]]  # C10 replaced by C11


def test_a_criterion_no_answer_replaced_is_its_own_class() -> None:
    versions = [contract(1, NINE, 0), contract(2, TEN, 10, answers="n1")]
    assert lineage_class(versions, "C1", stamp(20)) == frozenset({"C1"})  # a v1 criterion never removed and re-added
    assert lineage_class([contract(1, NINE, 0)], "C6", stamp(20)) == frozenset({"C6"})
    assert lineage_class([], "C3", stamp(20)) == frozenset({"C3"})  # no stored version at all


def test_a_class_holds_every_criterion_the_answers_that_added_its_text_replaced_transitively() -> None:
    versions = [contract(1, NINE, 0), contract(2, TEN, 10, answers="n1"), contract(3, ELEVEN, 20, answers="n2")]
    assert lineage_class(versions, "C10", stamp(30)) == frozenset({"C10", "C6"})
    assert lineage_class(versions, "C11", stamp(30)) == frozenset({"C11", "C10", "C6"})  # C11 replaced C10, which replaced C6
    assert lineage_class(versions, "C6", stamp(30)) == frozenset({"C6"})  # the older wording does not hold the newer one


def test_the_class_is_taken_as_of_a_time() -> None:
    versions = [contract(1, NINE, 0), contract(2, TEN, 10, answers="n1"), contract(3, ELEVEN, 20, answers="n2")]
    assert lineage_class(versions, "C11", stamp(15)) == frozenset({"C11"})  # before v3 was defined, C11 replaced nothing
    assert lineage_class(versions, "C10", stamp(15)) == frozenset({"C10", "C6"})
    assert lineage_class(versions, "C10", stamp(5)) == frozenset({"C10"})  # before v2 was defined, C10 replaced nothing


def test_two_rejections_fail_one_criterion_when_their_classes_meet() -> None:
    versions = [contract(1, NINE, 0), contract(2, TEN, 10, answers="n1")]
    first, second = lineage_class(versions, "C6", stamp(5)), lineage_class(versions, "C10", stamp(20))
    assert first & second == {"C6"}  # the rejection about C6 and the one about C10 are about one criterion
    assert not lineage_class(versions, "C1", stamp(20)) & second  # an unrelated criterion's class does not meet it
