"""``StepsPlaybookWriter``: the playbook v1 of every service of the example blueprints is the one the flat module wrote."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import pytest

from orgmcp.blueprint._budgeting import BudgetPlanner
from orgmcp.blueprint._playbooks import StepsPlaybookWriter
from orgmcp.blueprint._protocols import PlaybookWriting

from ._plans import base_dir, golden, scrub
from .test_charters import agents_of

SERVICES = [key for key in golden()["playbooks"]]


@pytest.mark.parametrize("key", SERVICES)
def test_every_playbook_is_the_text_the_flat_module_wrote(key: str, tmp_path: Path) -> None:
    label, _, name = key.partition("/")
    bp, agents, _, base = agents_of(label, tmp_path)
    planner = BudgetPlanner()
    service = next(sv for sv in cast(list[dict[str, object]], bp["services"]) if sv["name"] == name)
    budget = planner.service_budgets(bp, agents)[name]
    assert scrub(StepsPlaybookWriter(planner).default_playbook(agents[0], agents, service, budget), base) == golden()["playbooks"][key]


def test_the_three_sections_come_in_order_and_the_budget_is_the_one_given(tmp_path: Path) -> None:
    bp, agents, _, _ = agents_of("research-service", tmp_path)
    text = StepsPlaybookWriter(BudgetPlanner()).default_playbook(agents[0], agents, bp["services"][0], 22)  # type: ignore[index]
    assert [m.group(0) for m in re.finditer(r"^## .*$", text, re.M)] == ["## Steps", "## Budget plan", "## Pitfalls"]
    assert "Request budget: 22 runs (the contract's)." in text


def test_a_lead_without_a_team_does_the_work_itself(tmp_path: Path) -> None:
    from orgmcp.blueprint.api import Agent

    lead = Agent(addr="lead", name="lead", parent=None, where="agents[lead]", role="Lead", kind="manager", model="m")
    text = StepsPlaybookWriter(BudgetPlanner()).default_playbook(lead, [lead], {"name": "s"}, 5)
    assert "Do the work yourself, following the request's deliverable and criteria exactly." in text and "Request budget: 5 runs" in text
