"""``quality_thresholds``: the tunable defaults of the quality view, read from the ``quality:`` mapping of ORG.md (pure; design 6, 14).

No threshold can make a denominator 0: every count is at least 1 and the cost ratio is above 0."""

from __future__ import annotations

from fractions import Fraction

import pytest

from hirearchy.reflection import QUALITY_DEFAULTS, QualityThresholds, quality_thresholds

COUNTS = ("min_judged", "repeat_window", "repeat_failures")
WHAT = "a whole number of at least 1"
KEYS = "min_judged, repeat_window, repeat_failures, cost_ratio"


def read(**quality: object) -> tuple[QualityThresholds, tuple[str, ...]]:
    return quality_thresholds({"mission": "m", "quality": quality})


def test_defaults_without_a_quality_mapping() -> None:
    expected = QualityThresholds(3, 3, 2, Fraction("1.25"), "1.25", "defaults")
    assert quality_thresholds({}) == (expected, ())
    assert quality_thresholds({"mission": "m", "health": {"stuck_after_seconds": 5}}) == (expected, ())
    assert dict(QUALITY_DEFAULTS) == {"min_judged": 3, "repeat_window": 3, "repeat_failures": 2, "cost_ratio": "1.25"}
    assert QualityThresholds() == expected


@pytest.mark.parametrize("value", [5, 5.0, "5", "005"])
@pytest.mark.parametrize("key", COUNTS)
def test_each_count_key_accepts_an_int_an_integral_float_or_a_digit_string(key: str, value: object) -> None:
    given = {"repeat_window": 9, key: value}  # a window of 9 leaves room for repeat_failures
    got, notes = read(**given)
    assert notes == () and got.source == "ORG.md"
    assert getattr(got, key) == int(float(str(value)))
    assert isinstance(getattr(got, key), int)


@pytest.mark.parametrize("value", [True, False, 0, -1, 0.0, 2.5, "0", "-3", "two", "2.0", " 2", "", None, [2], float("inf"), float("nan")])
def test_a_bool_or_a_value_below_one_keeps_its_default_with_its_note(value: object) -> None:
    got, notes = read(min_judged=value)
    assert got.min_judged == 3 and got.source == "defaults"
    assert notes == (f"quality.min_judged in ORG.md is not {WHAT}: the default 3 is used.",)
    got, notes = read(repeat_window=value)
    assert got.repeat_window == 3
    assert notes == (f"quality.repeat_window in ORG.md is not {WHAT}: the default 3 is used.",)


def test_repeat_failures_above_the_window_keeps_its_default() -> None:
    got, notes = read(repeat_window=3, repeat_failures=5)
    assert got.repeat_failures == 2
    assert notes == ("quality.repeat_failures in ORG.md is not a whole number from 1 to 3: the default 2 is used.",)
    ok, none = read(repeat_window=3, repeat_failures=3)
    assert ok.repeat_failures == 3 and none == ()  # as many as the window is allowed
    assert read(repeat_failures=0)[1] == ("quality.repeat_failures in ORG.md is not a whole number from 1 to 3: the default 2 is used.",)


def test_the_window_is_settled_before_repeat_failures_is_checked() -> None:
    got, notes = read(repeat_window="bad", repeat_failures=3)  # the window falls back to 3, so 3 failures are allowed
    assert (got.repeat_window, got.repeat_failures) == (3, 3)
    assert notes == (f"quality.repeat_window in ORG.md is not {WHAT}: the default 3 is used.",)
    got, notes = read(repeat_window=4, repeat_failures=4)
    assert (got.repeat_window, got.repeat_failures, notes) == (4, 4, ())


def test_a_window_below_two_clamps_the_default_repeat_failures_with_its_note() -> None:
    got, notes = read(repeat_window=1)
    assert (got.repeat_window, got.repeat_failures) == (1, 1)
    assert notes == ("quality.repeat_failures: the default 2 is above repeat_window 1, so 1 is used.",)
    got, notes = read(repeat_window=1, repeat_failures=1)  # given, and allowed: no clamp, no note
    assert (got.repeat_failures, notes) == (1, ())
    assert read(repeat_window=2)[1] == ()  # the default 2 fits a window of 2


@pytest.mark.parametrize(
    ("value", "ratio", "shown"),
    [(2, Fraction(2), "2"), (1.5, Fraction(3, 2), "1.5"), ("1.30", Fraction(13, 10), "1.30"), ("2", Fraction(2), "2"), (0.1, Fraction(1, 10), "0.1")],
)
def test_cost_ratio_is_held_as_a_fraction_and_shown_as_written(value: object, ratio: Fraction, shown: str) -> None:
    got, notes = read(cost_ratio=value)
    assert (got.cost_ratio, got.cost_ratio_text, got.source, notes) == (ratio, shown, "ORG.md", ())
    assert isinstance(got.cost_ratio, Fraction)


@pytest.mark.parametrize("value", [True, False, 0, 0.0, -1.5, float("inf"), float("nan"), "0", "0.0", "-1", "1e3", "1,5", "abc", "", None, [1], {"a": 1}])
def test_a_cost_ratio_that_is_a_bool_not_finite_or_not_above_zero_keeps_its_default(value: object) -> None:
    got, notes = read(cost_ratio=value)
    assert (got.cost_ratio, got.cost_ratio_text, got.source) == (Fraction("1.25"), "1.25", "defaults")
    assert notes == ("quality.cost_ratio in ORG.md is not a number above 0: the default 1.25 is used.",)


def test_an_unknown_key_is_ignored_with_its_note() -> None:
    got, notes = read(min_judged=4, colour="red", cost_ratios=2)
    assert got.min_judged == 4 and got.cost_ratio == Fraction("1.25")
    assert notes == (
        f"quality.colour in ORG.md is not a threshold: ignored (the thresholds are {KEYS}).",
        f"quality.cost_ratios in ORG.md is not a threshold: ignored (the thresholds are {KEYS}).",
    )
    only_unknown, _ = read(colour="red")
    assert only_unknown.source == "defaults"  # nothing from ORG.md applied


@pytest.mark.parametrize("value", [5, "high", ["min_judged"], None, True])
def test_a_quality_value_that_is_not_a_mapping_is_ignored_with_its_note(value: object) -> None:
    got, notes = quality_thresholds({"quality": value})
    assert got == QualityThresholds()
    assert notes == ("quality in ORG.md is not a mapping: the defaults are used.",)


def test_every_threshold_can_be_set_at_once() -> None:
    got, notes = read(min_judged=2, repeat_window=5, repeat_failures=3, cost_ratio="1.5")
    assert got == QualityThresholds(2, 5, 3, Fraction(3, 2), "1.5", "ORG.md") and notes == ()
