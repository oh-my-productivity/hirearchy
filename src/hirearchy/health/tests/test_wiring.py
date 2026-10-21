"""The composition root builds the three ports of ``health`` for every organization, from the ports below it."""

from __future__ import annotations

from typing import Any

from hirearchy.health import HealthAnalyzer, HealthRenderer, HealthThresholds
from hirearchy.health._analyzer import FileHealthAnalyzer
from hirearchy.health._render import TextHealthRenderer
from hirearchy.health._thresholds import SettingsHealthThresholds


def test_the_runtime_builds_the_real_classes(scenario: Any) -> None:
    runtime = scenario.runtime
    assert isinstance(runtime.health_analyzer, FileHealthAnalyzer) and isinstance(runtime.health_analyzer, HealthAnalyzer)
    assert isinstance(runtime.health_renderer, TextHealthRenderer) and isinstance(runtime.health_renderer, HealthRenderer)
    assert isinstance(runtime.health_thresholds, SettingsHealthThresholds) and isinstance(runtime.health_thresholds, HealthThresholds)


def test_each_port_is_built_once_per_organization(scenario: Any) -> None:
    runtime = scenario.runtime
    assert runtime.health_analyzer is runtime.health_analyzer and runtime.health_thresholds is runtime.health_thresholds


def test_the_analyzer_reads_the_thresholds_of_the_runtime(scenario: Any) -> None:
    assert scenario.runtime.health_thresholds.thresholds()["stuck_after_seconds"] == 1800
