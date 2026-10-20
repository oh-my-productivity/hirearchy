"""What the analyzer and the renderer of the package (``health_analyzer``, ``health_renderer``, the ports of the runtime) say about the organization with
every flag in it, text for text and number for number, as ``health.py`` said it before the move."""

from __future__ import annotations

import json
from typing import Any

from . import _scenario
from ._golden import expected
NOW = {"4000": _scenario.at(4000), "3d": _scenario.at(3 * 86400)}


def test_the_text_of_the_whole_organization(scenario: Any) -> None:
    runtime = scenario.runtime
    report = runtime.health_analyzer.org_health("root", NOW["4000"])
    assert runtime.health_renderer.render_text(report) + "\n" == expected("org_4000.txt")


def test_the_text_three_days_later_has_idle_agents(scenario: Any) -> None:
    runtime = scenario.runtime
    report = runtime.health_analyzer.org_health("root", NOW["3d"])
    assert runtime.health_renderer.render_text(report) + "\n" == expected("org_3d.txt")


def test_the_text_of_one_branch(scenario: Any) -> None:
    runtime = scenario.runtime
    assert runtime.health_renderer.render_text(runtime.health_analyzer.org_health("ceo", NOW["4000"])) + "\n" == expected("ceo_4000.txt")


def test_the_json_of_the_whole_organization(scenario: Any) -> None:
    report = scenario.runtime.health_analyzer.org_health("root", NOW["4000"])
    assert json.dumps(report.to_dict(), indent=2) + "\n" == expected("org_4000.json")


def test_the_json_three_days_later(scenario: Any) -> None:
    report = scenario.runtime.health_analyzer.org_health("root", NOW["3d"])
    assert json.dumps(report.to_dict(), indent=2) + "\n" == expected("org_3d.json")


def test_one_agent_as_the_dataclass_prints_it(scenario: Any) -> None:
    assert repr(scenario.runtime.health_analyzer.agent_health("ceo/eng", NOW["4000"])) + "\n" == expected("eng_4000_repr.txt")


def test_the_default_now_is_the_clock_of_the_runtime(scenario: Any) -> None:
    scenario.runtime.clock  # the patched core.utcnow: it advances a millisecond per reading
    first = scenario.runtime.health_analyzer.org_health().now
    second = scenario.runtime.health_analyzer.org_health().now
    assert second > first
