"""Characterization: what ``org_health``, ``agent_health``, ``to_dict`` and ``render_text`` say about the scenario organization.

The expected files were captured from ``health.py`` before the move, so these tests prove the package says the same, text for text and number
for number. They run through the legacy functions here; ``test_golden_ports.py`` runs the same comparison through the runtime's ports."""

from __future__ import annotations

import json
from typing import Any

from orgmcp.health import agent_health, org_health, render_text

from . import _scenario
from ._golden import expected

NOW = {"4000": _scenario.at(4000), "3d": _scenario.at(3 * 86400)}


def test_the_text_of_the_whole_organization(scenario: Any) -> None:
    assert render_text(org_health(scenario, "root", NOW["4000"])) + "\n" == expected("org_4000.txt")


def test_the_text_three_days_later_has_idle_agents(scenario: Any) -> None:
    assert render_text(org_health(scenario, "root", NOW["3d"])) + "\n" == expected("org_3d.txt")


def test_the_text_of_one_branch(scenario: Any) -> None:
    assert render_text(org_health(scenario, "ceo", NOW["4000"])) + "\n" == expected("ceo_4000.txt")


def test_the_json_of_the_whole_organization(scenario: Any) -> None:
    assert json.dumps(org_health(scenario, "root", NOW["4000"]).to_dict(), indent=2) + "\n" == expected("org_4000.json")


def test_the_json_three_days_later(scenario: Any) -> None:
    assert json.dumps(org_health(scenario, "root", NOW["3d"]).to_dict(), indent=2) + "\n" == expected("org_3d.json")


def test_one_agent_as_the_dataclass_prints_it(scenario: Any) -> None:
    assert repr(agent_health(scenario, "ceo/eng", NOW["4000"])) + "\n" == expected("eng_4000_repr.txt")
