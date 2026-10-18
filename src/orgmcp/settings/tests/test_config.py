"""The pure rules for reading a value out of the settings mapping, pinned against the answers of the legacy functions."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from orgmcp.settings import (
    DEFAULT_CONFIG,
    DEFAULT_MODEL,
    config_default_model,
    config_message_cap,
    config_number,
    finite_number,
)
from orgmcp.settings.tests import _tables


def test_the_default_model_is_one_constant() -> None:
    assert DEFAULT_MODEL == "claude-sonnet-5.5"
    assert DEFAULT_CONFIG["default_model"] == DEFAULT_MODEL


def test_the_defaults_are_exactly_these() -> None:
    assert DEFAULT_CONFIG == {
        "max_depth": 4, "max_hops": 40, "max_parallel": 3, "max_failures": 3, "run_timeout": 1800, "stall_after": 600,
        "review_every_runs": 25, "review_every_seconds": 86400, "poll_seconds": 2, "until_done_grace_seconds": 300,
        "default_budget": 10, "memory_max_words": 800, "playbook_max_words": 1000, "default_model": "claude-sonnet-5.5",
        "max_message_chars": 20000, "events": True, "events_keep_days": 30, "heartbeat_seconds": 60,
    }
    assert list(DEFAULT_CONFIG)[:3] == ["max_depth", "max_hops", "max_parallel"]  # the order is the order ORG.md is written in


@pytest.mark.parametrize("value, expected", _tables.FINITE_NUMBER, ids=lambda v: repr(v)[:24])
def test_finite_number(value: object, expected: float | None) -> None:
    got = finite_number(value)
    assert got == expected and type(got) is type(expected)


@pytest.mark.parametrize("config, key, kind, expected", _tables.CONFIG_NUMBER, ids=lambda v: repr(v)[:30])
def test_config_number(config: dict[str, object], key: str, kind: type[float] | type[int], expected: float) -> None:
    got = config_number(config, key, kind)
    assert got == expected and type(got) is kind


def test_config_number_defaults_to_float() -> None:
    got = config_number({}, "poll_seconds")
    assert got == 2.0 and type(got) is float


def test_a_key_that_has_no_default_is_an_error_when_it_is_missing() -> None:
    with pytest.raises(KeyError):
        config_number({}, "no_such_setting")
    assert config_number({"no_such_setting": 7}, "no_such_setting", int) == 7


@pytest.mark.parametrize("config, expected", _tables.DEFAULT_MODEL_OF, ids=lambda v: repr(v)[:30])
def test_config_default_model(config: Mapping[str, object] | None, expected: str) -> None:
    assert config_default_model(config) == expected


@pytest.mark.parametrize("config, expected", _tables.MESSAGE_CAP, ids=lambda v: repr(v)[:30])
def test_config_message_cap(config: Mapping[str, object], expected: int) -> None:
    assert config_message_cap(config) == expected
