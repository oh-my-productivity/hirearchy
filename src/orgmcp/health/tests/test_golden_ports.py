"""The same comparison as ``test_golden_report.py``, through the ports of the runtime (``health_analyzer``, ``health_renderer``): the analyzer
and the renderer of the package say what ``health.py`` said, text for text and number for number, on the organization with every flag in it."""

from __future__ import annotations

import json
from typing import Any

from orgmcp.health import agent_health, org_health, render_text

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


def test_the_legacy_functions_and_the_ports_agree_on_everything(scenario: Any) -> None:
    runtime = scenario.runtime
    for now in NOW.values():
        for top in ("root", "ceo", "ops", "ceo/eng"):
            assert org_health(scenario, top, now) == runtime.health_analyzer.org_health(top, now)
            assert render_text(org_health(scenario, top, now)) == runtime.health_renderer.render_text(runtime.health_analyzer.org_health(top, now))
        for addr in scenario.agents():
            assert agent_health(scenario, addr, now) == runtime.health_analyzer.agent_health(addr, now)


def test_the_default_now_is_the_clock_of_the_runtime(scenario: Any) -> None:
    scenario.runtime.clock  # the patched core.utcnow: it advances a millisecond per reading
    first = scenario.runtime.health_analyzer.org_health().now
    second = scenario.runtime.health_analyzer.org_health().now
    assert second > first
