"""``retro_thresholds``: the tunable defaults of the retro brief, read from the ``retro:`` mapping of ORG.md (pure; design 4.9).

A value that fails keeps its default and adds a note; an unknown key and a ``retro`` that is no mapping are ignored with a note. No threshold can
make a denominator 0: every count is at least 1 (``carry`` may be 0) and the ratios are above 0."""

from __future__ import annotations

from fractions import Fraction

import pytest

from hirearchy.retro import RETRO_DEFAULTS, RetroThresholds, retro_thresholds

KEYS = (
    "after_verdicts, window, carry, items, shape_cases, shape_overlap, criterion_cases, escapes, window_cases, saturation, added_words, accepted_cases"
)
COUNTS = {  # key -> (the default, the words of its note)
    "after_verdicts": (3, "a whole number of at least 1"),
    "window": (3, "a whole number of at least 1"),
    "carry": (3, "a whole number of at least 0"),
    "shape_cases": (3, "a whole number of at least 2"),
    "criterion_cases": (3, "a whole number of at least 2"),
    "escapes": (2, "a whole number of at least 1"),
    "window_cases": (10, "a whole number of at least 3"),
    "added_words": (3, "a whole number of at least 1"),
    "accepted_cases": (3, "a whole number of at least 1"),
}
LOWEST = {"after_verdicts": 1, "window": 1, "carry": 0, "shape_cases": 2, "criterion_cases": 2, "escapes": 1, "window_cases": 3, "added_words": 1, "accepted_cases": 1}


def read(**retro: object) -> tuple[RetroThresholds, tuple[str, ...]]:
    return retro_thresholds({"mission": "m", "retro": retro})


def test_the_defaults_are_4_9s() -> None:
    expected = RetroThresholds(3, 3, 3, 3, 3, Fraction("0.6"), "0.6", 3, 2, 10, Fraction("0.45"), "0.45", 3, 3, "defaults")
    assert retro_thresholds({}) == (expected, ())
    assert retro_thresholds({"mission": "m", "quality": {"min_judged": 4}}) == (expected, ())
    assert RetroThresholds() == expected
    assert dict(RETRO_DEFAULTS) == {
        "after_verdicts": 3, "window": 3, "carry": 3, "items": 3, "shape_cases": 3, "shape_overlap": "0.6", "criterion_cases": 3, "escapes": 2,
        "window_cases": 10, "saturation": "0.45", "added_words": 3, "accepted_cases": 3,
    }
    assert expected.shape_overlap == Fraction(3, 5) and expected.saturation == Fraction(9, 20)


@pytest.mark.parametrize("value", [5, 5.0, "5", "005"])
@pytest.mark.parametrize("key", COUNTS)
def test_each_count_key_accepts_an_int_an_integral_float_or_a_digit_string(key: str, value: object) -> None:
    got, notes = read(**{key: value})
    assert notes == () and got.source == "ORG.md"
    assert getattr(got, key) == 5 and isinstance(getattr(got, key), int)


@pytest.mark.parametrize("value", [True, False, -1, 2.5, "two", "2.0", " 2", "", None, [2], float("inf"), float("nan")])
@pytest.mark.parametrize("key", COUNTS)
def test_a_bad_value_keeps_its_default_with_a_note(key: str, value: object) -> None:
    default, what = COUNTS[key]
    got, notes = read(**{key: value})
    assert getattr(got, key) == default and got.source == "defaults"
    assert notes == (f"retro.{key} in ORG.md is not {what}: the default {default} is used.",)


@pytest.mark.parametrize("key", COUNTS)
def test_a_count_below_its_lowest_keeps_its_default_and_the_lowest_is_accepted(key: str) -> None:
    default, what = COUNTS[key]
    lowest = LOWEST[key]
    got, notes = read(**{key: lowest})
    assert getattr(got, key) == lowest and notes == ()
    if lowest > 0:
        got, notes = read(**{key: lowest - 1})
        assert getattr(got, key) == default and notes == (f"retro.{key} in ORG.md is not {what}: the default {default} is used.",)


@pytest.mark.parametrize(("value", "kept"), [(1, 1), (2, 2), (3, 3), ("2", 2), (2.0, 2)])
def test_items_takes_1_2_or_3(value: object, kept: int) -> None:
    got, notes = read(items=value)
    assert got.items == kept and notes == () and got.source == "ORG.md"


@pytest.mark.parametrize("value", [4, 10, "7", 4.0])
def test_items_above_3_keeps_3_with_a_note(value: object) -> None:
    got, notes = read(items=value)
    assert got.items == 3 and got.source == "ORG.md"
    assert notes == ("retro.items in ORG.md is above 3: 3 is used (a brief has at most 3 items).",)


@pytest.mark.parametrize("value", [0, -1, True, False, 2.5, "two", "", None, [1], float("inf")])
def test_items_that_is_not_a_whole_number_of_at_least_1_keeps_its_default(value: object) -> None:
    got, notes = read(items=value)
    assert got.items == 3 and got.source == "defaults"
    assert notes == ("retro.items in ORG.md is not 1, 2 or 3: the default 3 is used.",)


@pytest.mark.parametrize(
    ("key", "value", "ratio", "shown"),
    [
        ("shape_overlap", 0.5, Fraction(1, 2), "0.5"), ("shape_overlap", "0.75", Fraction(3, 4), "0.75"), ("shape_overlap", 1, Fraction(1), "1"),
        ("shape_overlap", "1", Fraction(1), "1"), ("saturation", 0.3, Fraction(3, 10), "0.3"), ("saturation", "0.50", Fraction(1, 2), "0.50"),
    ],
)
def test_the_ratios_are_held_as_fractions_and_shown_as_written(key: str, value: object, ratio: Fraction, shown: str) -> None:
    got, notes = read(**{key: value})
    assert (getattr(got, key), getattr(got, f"{key}_text"), got.source, notes) == (ratio, shown, "ORG.md", ())
    assert isinstance(getattr(got, key), Fraction)


@pytest.mark.parametrize("value", [True, False, 0, 0.0, -0.5, 1.5, 2, float("inf"), float("nan"), "0", "0.0", "1.5", "-1", "1e-1", "1,5", "abc", "", None, [0.5]])
def test_shape_overlap_must_be_a_decimal_above_0_and_at_most_1(value: object) -> None:
    got, notes = read(shape_overlap=value)
    assert (got.shape_overlap, got.shape_overlap_text, got.source) == (Fraction("0.6"), "0.6", "defaults")
    assert notes == ("retro.shape_overlap in ORG.md is not a decimal above 0 and at most 1: the default 0.6 is used.",)


@pytest.mark.parametrize("value", [True, 0, 0.0, 1, 1.0, "1", "1.0", 2, "x", None, float("nan")])
def test_saturation_must_be_a_decimal_above_0_and_below_1(value: object) -> None:
    got, notes = read(saturation=value)
    assert (got.saturation, got.saturation_text, got.source) == (Fraction("0.45"), "0.45", "defaults")
    assert notes == ("retro.saturation in ORG.md is not a decimal above 0 and below 1: the default 0.45 is used.",)


def test_an_unknown_key_and_a_non_mapping_retro_are_ignored_with_a_note() -> None:
    got, notes = read(after_verdicts=4, colour="red", windows=2)
    assert got.after_verdicts == 4 and got.window == 3
    assert notes == (
        f"retro.colour in ORG.md is not a threshold: ignored (the thresholds are {KEYS}).",
        f"retro.windows in ORG.md is not a threshold: ignored (the thresholds are {KEYS}).",
    )
    only_unknown, _ = read(colour="red")
    assert only_unknown.source == "defaults"  # nothing from ORG.md applied
    for value in (5, "high", ["window"], None, True):
        assert retro_thresholds({"retro": value}) == (RetroThresholds(), ("retro in ORG.md is not a mapping: the defaults are used.",))


def test_every_threshold_can_be_set_at_once() -> None:
    got, notes = read(
        after_verdicts=2, window=4, carry=0, items=2, shape_cases=4, shape_overlap="0.8", criterion_cases=4, escapes=3, window_cases=12,
        saturation="0.4", added_words=2, accepted_cases=5,
    )
    assert got == RetroThresholds(2, 4, 0, 2, 4, Fraction("0.8"), "0.8", 4, 3, 12, Fraction("0.4"), "0.4", 2, 5, "ORG.md") and notes == ()


def test_the_thresholds_are_read_from_a_config_that_may_hold_other_keys() -> None:
    got, notes = retro_thresholds({"mission": "m", "quality": {"min_judged": 2}, "health": {}, "retro": {"window": 2}})
    assert got.window == 2 and notes == ()
