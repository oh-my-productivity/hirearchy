"""The org-agent floor: the allowed models, the effort levels and the wording of every refusal (docs/design/org-agent-model-floor.md)."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from hirearchy.settings import (
    DEFAULT_ALLOWED_MODELS,
    DEFAULT_CONFIG,
    DEFAULT_EFFORT,
    DEFAULT_MODEL,
    EFFORT_LEVELS,
    config_allowed_models,
    config_effort,
    config_floor_problem,
    effort_floor_problem,
    model_floor_problem,
)

PAIR = "claude-sonnet-5.5, claude-opus-5.5"


def m1(model: str, allowed: str = PAIR) -> str:
    return f'model "{model}" is not allowed for org agents; allowed: {allowed} (only the user can widen this set)'


def m2(value: str) -> str:
    return f'effort "{value}" is not allowed for org agents; allowed: high, xhigh, max'


def test_the_default_allowed_models_are_the_floor_pair_and_hold_the_default_model() -> None:
    assert DEFAULT_ALLOWED_MODELS == ("claude-sonnet-5.5", "claude-opus-5.5")
    assert DEFAULT_MODEL in DEFAULT_ALLOWED_MODELS


def test_the_effort_levels_and_the_default_effort() -> None:
    assert EFFORT_LEVELS == ("high", "xhigh", "max")
    assert DEFAULT_EFFORT == DEFAULT_CONFIG["effort"] == "high"
    keys = list(DEFAULT_CONFIG)
    assert keys[keys.index("default_model") + 1] == "effort"


@pytest.mark.parametrize(
    "config, expected",
    [
        (None, "high"),
        ({}, "high"),
        ({"effort": None}, "high"),
        ({"effort": ""}, "high"),
        ({"effort": "  "}, "high"),
        ({"effort": "xhigh"}, "xhigh"),
        ({"effort": " max "}, "max"),
        ({"effort": "High"}, "High"),
        ({"effort": "low"}, "low"),
        ({"effort": 5}, "5"),
    ],
    ids=lambda v: repr(v)[:24],
)
def test_config_effort_reads_the_value_or_high(config: Mapping[str, object] | None, expected: str) -> None:
    assert config_effort(config) == expected


@pytest.mark.parametrize(
    "config, expected",
    [
        (None, DEFAULT_ALLOWED_MODELS),
        ({}, DEFAULT_ALLOWED_MODELS),
        ({"extra_allowed_models": None}, DEFAULT_ALLOWED_MODELS),
        ({"extra_allowed_models": ["claude-sonnet-4.6"]}, (*DEFAULT_ALLOWED_MODELS, "claude-sonnet-4.6")),
        ({"extra_allowed_models": "claude-sonnet-4.6"}, (*DEFAULT_ALLOWED_MODELS, "claude-sonnet-4.6")),
        ({"extra_allowed_models": [" claude-sonnet-4.6 ", "", "  ", 7, None, "claude-sonnet-4.6"]}, (*DEFAULT_ALLOWED_MODELS, "claude-sonnet-4.6")),
        ({"extra_allowed_models": ["claude-opus-5.5", "claude-haiku-4.5"]}, (*DEFAULT_ALLOWED_MODELS, "claude-haiku-4.5")),
        ({"extra_allowed_models": ""}, DEFAULT_ALLOWED_MODELS),
        ({"extra_allowed_models": 7}, DEFAULT_ALLOWED_MODELS),
    ],
    ids=lambda v: repr(v)[:40],
)
def test_config_allowed_models_adds_extra_ids_after_the_pair(config: Mapping[str, object] | None, expected: tuple[str, ...]) -> None:
    assert config_allowed_models(config) == expected


@pytest.mark.parametrize("model", ["claude-haiku-4.5", "claude-sonnet-4.6", "m", ""])
def test_model_floor_problem_refuses_ids_outside_the_set(model: str) -> None:
    assert model_floor_problem({}, model) == m1(model)


@pytest.mark.parametrize("model", ["claude-sonnet-5.5", "claude-opus-5.5"])
def test_model_floor_problem_admits_the_floor_models(model: str) -> None:
    assert model_floor_problem({}, model) is None
    assert model_floor_problem(None, model) is None


def test_a_widened_set_admits_its_extra_id_and_names_all_three() -> None:
    config = {"extra_allowed_models": ["claude-sonnet-4.6"]}
    assert model_floor_problem(config, "claude-sonnet-4.6") is None
    assert model_floor_problem(config, "claude-haiku-4.5") == m1("claude-haiku-4.5", PAIR + ", claude-sonnet-4.6")


@pytest.mark.parametrize("value", ["low", "medium", "High", "", "extreme"])
def test_effort_floor_problem_refuses_levels_outside_the_set(value: str) -> None:
    assert effort_floor_problem(value) == m2(value)


@pytest.mark.parametrize("value", ["high", "xhigh", "max"])
def test_effort_floor_problem_admits_the_levels(value: str) -> None:
    assert effort_floor_problem(value) is None


def test_config_floor_problem_without_before() -> None:
    assert config_floor_problem(dict(DEFAULT_CONFIG)) is None
    assert config_floor_problem({}) is None
    assert config_floor_problem({"effort": "low"}) == m2("low")
    assert config_floor_problem({"default_model": "claude-haiku-4.5"}) == "default_model: " + m1("claude-haiku-4.5")
    widened = {"extra_allowed_models": ["claude-haiku-4.5"], "default_model": "claude-haiku-4.5"}
    assert config_floor_problem(widened) is None
    # the effort is reported first when both are bad
    assert config_floor_problem({"effort": "medium", "default_model": "claude-haiku-4.5"}) == m2("medium")


def test_config_floor_problem_tolerates_what_before_had_and_refuses_a_widening() -> None:
    haiku = {"default_model": "claude-haiku-4.5", "effort": "low"}
    # what the organization already had is tolerated
    assert config_floor_problem(haiku, before=haiku) is None
    assert config_floor_problem({"default_model": "claude-haiku-4.5"}, before={"default_model": "claude-haiku-4.5"}) is None
    assert config_floor_problem({"effort": "low"}, before={"effort": "low"}) is None
    # a change to a value outside the floor is not
    assert config_floor_problem({"default_model": "claude-haiku-4.5"}, before={"default_model": "claude-sonnet-5.5"}) == (
        "default_model: " + m1("claude-haiku-4.5")
    )
    assert config_floor_problem({"effort": "medium"}, before={"effort": "high"}) == m2("medium")
    # widening the set is refused, and names the ids that would be added
    assert config_floor_problem({"extra_allowed_models": ["claude-sonnet-4.6"]}, before={}) == (
        "only the user can widen the allowed models, by editing ORG.md themselves (not allowed now: claude-sonnet-4.6)"
    )
    # the same extras, or fewer, are fine
    same = {"extra_allowed_models": ["claude-sonnet-4.6"]}
    assert config_floor_problem(same, before=same) is None
    assert config_floor_problem({}, before=same) is None
    assert config_floor_problem({"extra_allowed_models": ["claude-sonnet-4.6"]}, before={"extra_allowed_models": ["claude-sonnet-4.6", "x"]}) is None
