"""``StepsPlaybookWriter``: the playbook v1 of every service of the example blueprints is the one the flat module wrote."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import pytest

from hirearchy.blueprint._budgeting import BudgetPlanner
from hirearchy.blueprint._playbooks import StepsPlaybookWriter
from hirearchy.blueprint._protocols import PlaybookWriting

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


def test_the_two_sections_come_in_order_and_the_budget_is_the_one_given(tmp_path: Path) -> None:
    bp, agents, _, _ = agents_of("research-service", tmp_path)
    text = StepsPlaybookWriter(BudgetPlanner()).default_playbook(agents[0], agents, bp["services"][0], 22)  # type: ignore[index]
    assert [m.group(0) for m in re.finditer(r"^## .*$", text, re.M)] == ["## Steps", "## Budget plan"]
    assert "Request budget: 22 runs (the contract's)." in text


def test_a_lead_without_a_team_does_the_work_itself(tmp_path: Path) -> None:
    from hirearchy.blueprint.api import Agent

    lead = Agent(addr="lead", name="lead", parent=None, where="agents[lead]", role="Lead", kind="manager", model="m")
    text = StepsPlaybookWriter(BudgetPlanner()).default_playbook(lead, [lead], {"name": "s"}, 5)
    assert "Do the work yourself, following the request's deliverable and criteria exactly." in text and "Request budget: 5 runs" in text


LEFTOVER = "On this first run delegate only the steps that need nothing from a teammate"


@pytest.mark.parametrize("key", SERVICES)
def test_the_default_playbook_has_no_first_run_leftover(key: str, tmp_path: Path) -> None:
    label, _, name = key.partition("/")
    bp, agents, _, _ = agents_of(label, tmp_path)
    planner = BudgetPlanner()
    service = next(sv for sv in cast(list[dict[str, object]], bp["services"]) if sv["name"] == name)
    text = StepsPlaybookWriter(planner).default_playbook(agents[0], agents, service, planner.service_budgets(bp, agents)[name])
    assert LEFTOVER not in text and LEFTOVER not in golden()["playbooks"][key]


def test_the_first_maker_step_ends_with_the_criteria_it_must_meet(tmp_path: Path) -> None:
    bp, agents, _, _ = agents_of("research-service", tmp_path)
    text = StepsPlaybookWriter(BudgetPlanner()).default_playbook(agents[0], agents, bp["services"][0], 22)  # type: ignore[index]
    first = next(line for line in text.splitlines() if line.startswith("2. Delegate to "))
    assert first.endswith(" with `budget=4`: its part of the request, with the criteria it must meet.")


@pytest.mark.parametrize("key", SERVICES)
def test_the_last_step_asks_for_the_aar_form(key: str, tmp_path: Path) -> None:
    label, _, name = key.partition("/")
    bp, agents, _, _ = agents_of(label, tmp_path)
    planner = BudgetPlanner()
    service = next(sv for sv in cast(list[dict[str, object]], bp["services"]) if sv["name"] == name)
    text = StepsPlaybookWriter(planner).default_playbook(agents[0], agents, service, planner.service_budgets(bp, agents)[name])
    last = text.split("## Budget plan")[0].rstrip().splitlines()[-1]
    assert last.endswith(
        "and pass `lessons` as an after-action review: Expected / Happened / Caught at / Cause / Prevent (the system cause, not a person), "
        "or Near miss when nothing went wrong."
    )
    assert "1-3 lines" not in text and "what to change in this playbook" not in text


@pytest.mark.parametrize("key", SERVICES)
def test_there_is_no_pitfalls_placeholder(key: str, tmp_path: Path) -> None:
    label, _, name = key.partition("/")
    bp, agents, _, _ = agents_of(label, tmp_path)
    planner = BudgetPlanner()
    service = next(sv for sv in cast(list[dict[str, object]], bp["services"]) if sv["name"] == name)
    text = StepsPlaybookWriter(planner).default_playbook(agents[0], agents, service, planner.service_budgets(bp, agents)[name])
    assert "Pitfalls" not in text and "none yet" not in text
    assert [m.group(0) for m in re.finditer(r"^## .*$", text, re.M)] == ["## Steps", "## Budget plan"]
    assert text.rstrip().endswith("Unspent runs return to your parent with your final report.")
