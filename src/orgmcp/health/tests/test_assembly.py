"""The analyzer over the ports an ``Org`` has now (``_assembly``): the settings and the run count are the ``Org``'s own, everything else is its runtime's."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from orgmcp.health import HEALTH_DEFAULTS, HealthAnalyzer, HealthThresholds
from orgmcp.health._assembly import analyzer_of, thresholds_of
from orgmcp.health._ports import CallableConfig, CallableRunCount, ConfigSource, RunCount

from . import _scenario

NOW = _scenario.at(4000)


def host(scenario: Any, **overrides: Any) -> Any:
    """What the legacy functions are given, with some of the ``Org``'s answers replaced."""
    answers: dict[str, Any] = {"config": scenario.config, "runs_used": scenario.runs_used} | overrides
    return SimpleNamespace(runtime=scenario.runtime, **answers)


def test_the_callable_ports_answer_with_their_function() -> None:
    assert isinstance(CallableConfig(lambda: {"a": 1}), ConfigSource) and CallableConfig(lambda: {"a": 1}).config() == {"a": 1}
    assert isinstance(CallableRunCount(lambda addr: len(addr)), RunCount) and CallableRunCount(lambda addr: len(addr)).count("ceo") == 3


def test_the_thresholds_are_those_of_the_config_the_org_gives(scenario: Any) -> None:
    assert isinstance(thresholds_of(host(scenario)), HealthThresholds)
    assert thresholds_of(host(scenario)).thresholds() == HEALTH_DEFAULTS
    soft = host(scenario, config={"health": {"idle_after_seconds": 5}})
    assert thresholds_of(soft).thresholds()["idle_after_seconds"] == 5


def test_the_runs_used_are_those_the_org_counts(scenario: Any) -> None:
    assert isinstance(analyzer_of(host(scenario)), HealthAnalyzer)
    assert analyzer_of(host(scenario)).agent_health("ceo/eng", NOW).runs_used == 8
    counted = host(scenario, runs_used=lambda addr: 99)
    assert analyzer_of(counted).agent_health("ceo/eng", NOW).runs_used == 99


def test_the_limits_are_those_of_the_config_the_org_gives(scenario: Any) -> None:
    soft = host(scenario, config={"health": {"stuck_after_seconds": 10 ** 9}})
    assert "stuck" in analyzer_of(host(scenario)).agent_health("ceo/eng", NOW).flags
    assert "stuck" not in analyzer_of(soft).agent_health("ceo/eng", NOW).flags
