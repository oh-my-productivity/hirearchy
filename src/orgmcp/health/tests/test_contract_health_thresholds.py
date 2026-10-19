"""Contract of ``HealthThresholds``: the numbers where the flags start - the defaults, with the ``health:`` block of ORG.md over them.

A value that is not a finite number falls back to its default, so that a mistake in ORG.md cannot break health."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.health import HEALTH_DEFAULTS, HealthThresholds
from orgmcp.health.testing import IMPLEMENTATIONS, ThresholdsHarness

from ._support import implementations


@pytest.fixture(params=implementations(IMPLEMENTATIONS[HealthThresholds]))
def t(request: pytest.FixtureRequest, tmp_path: Path) -> ThresholdsHarness:
    made = cast(Callable[[Path], ThresholdsHarness], request.param)(tmp_path)
    assert isinstance(made.thresholds, HealthThresholds)
    return made


def health_block(*lines: str) -> str:
    return "---\nmission: test\nhealth:\n" + "".join(f"  {line}\n" for line in lines) + "---\nrules\n"


def test_without_a_health_block_the_thresholds_are_the_defaults(t: ThresholdsHarness) -> None:
    assert t.thresholds.thresholds() == HEALTH_DEFAULTS


def test_the_answer_is_a_new_mapping_every_time(t: ThresholdsHarness) -> None:
    t.thresholds.thresholds()["stuck_after_seconds"] = 1
    assert t.thresholds.thresholds() == HEALTH_DEFAULTS and HEALTH_DEFAULTS["stuck_after_seconds"] == 1800


def test_the_values_of_the_block_override_the_defaults_one_by_one(t: ThresholdsHarness) -> None:
    t.configure(health_block("idle_after_seconds: 60", "max_problem_ratio: 0.25"))
    got = t.thresholds.thresholds()
    assert got["idle_after_seconds"] == 60 and got["max_problem_ratio"] == 0.25
    assert {k: v for k, v in got.items() if k not in ("idle_after_seconds", "max_problem_ratio")} == {
        k: v for k, v in HEALTH_DEFAULTS.items() if k not in ("idle_after_seconds", "max_problem_ratio")
    }


@pytest.mark.parametrize("literal", ["soon", "true", "false", ".inf", "-.inf", ".nan", "null", "[1, 2]", "{a: 1}", '""', "'1e999'"])
def test_a_value_that_is_not_a_finite_number_falls_back_to_its_default(t: ThresholdsHarness, literal: str) -> None:
    t.configure(health_block(f"stuck_after_seconds: {literal}", "idle_after_seconds: 60"))
    got = t.thresholds.thresholds()
    assert got["stuck_after_seconds"] == HEALTH_DEFAULTS["stuck_after_seconds"] and got["idle_after_seconds"] == 60


@pytest.mark.parametrize(("literal", "number"), [("'60'", 60), ("'0.75'", 0.75), ("' 5 '", 5), ("'1e2'", 100), ("7.0", 7.0), ("0", 0), ("-3", -3)])
def test_numbers_and_numeric_strings_are_numbers(t: ThresholdsHarness, literal: str, number: float) -> None:
    t.configure(health_block(f"max_runs_per_task: {literal}"))
    got = t.thresholds.thresholds()["max_runs_per_task"]
    assert got == number and not isinstance(got, bool)


@pytest.mark.parametrize("block", ["health: 5", "health: soon", "health: [1, 2]", "health:", "health: null"])
def test_a_health_entry_that_is_not_a_mapping_means_the_defaults(t: ThresholdsHarness, block: str) -> None:
    t.configure(f"---\nmission: test\n{block}\n---\nrules\n")
    assert t.thresholds.thresholds() == HEALTH_DEFAULTS


def test_a_key_that_is_not_a_threshold_is_carried_through_as_it_is(t: ThresholdsHarness) -> None:
    t.configure(health_block("custom_note: hello"))
    assert t.thresholds.thresholds() == {**HEALTH_DEFAULTS, "custom_note": "hello"}


def test_a_change_of_org_md_is_seen_at_the_next_call(t: ThresholdsHarness) -> None:
    t.configure(health_block("idle_after_seconds: 60"))
    assert t.thresholds.thresholds()["idle_after_seconds"] == 60
    t.configure(health_block("idle_after_seconds: 120"))
    assert t.thresholds.thresholds()["idle_after_seconds"] == 120
    t.configure("---\nmission: test\n---\nrules\n")
    assert t.thresholds.thresholds() == HEALTH_DEFAULTS
