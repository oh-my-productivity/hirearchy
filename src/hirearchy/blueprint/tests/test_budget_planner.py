"""``BudgetPlanner``: the runs a blueprint needs for one pass plus one rework cycle, and how they are split down the tree."""

from __future__ import annotations

import pytest

from hirearchy.blueprint._budgeting import KINDS, REWORK_RUNS, SLACK, TIGHT, BudgetPlanner, round_offer
from hirearchy.blueprint._protocols import BudgetPlanning
from hirearchy.blueprint.api import Agent

from ._support import role



def agent(addr: str, kind: str, children: tuple[str, ...] = (), runs: int | None = None, scale: int = 1) -> Agent:
    parent = addr.rsplit("/", 1)[0] if "/" in addr else None
    template = None if runs is None else role("writer", base_runs=runs)
    return Agent(addr, addr.rsplit("/", 1)[-1], parent, f"agents[{addr}]", template=template, kind=kind, children=list(children), scale=scale)


TEAM = [
    agent("lead", "manager", ("lead/researcher", "lead/writer", "lead/check")),
    agent("lead/researcher", "author", runs=3),
    agent("lead/writer", "author", runs=2),
    agent("lead/check", "verifier", runs=2),
]


def test_a_manager_plans_delegates_and_processes_each_result_and_reworks_twice() -> None:
    est = BudgetPlanner().estimate(TEAM)
    assert est["per"]["lead"] == {"pass": 5, "rework": 2, "total": 7}


def test_a_worker_costs_its_template_runs_times_its_scale_plus_one_rework() -> None:
    est = BudgetPlanner().estimate([agent("w", "author", runs=3, scale=2), agent("c", "author"), agent("v", "verifier", runs=1)])
    assert est["per"]["w"] == {"pass": 6, "rework": 1, "total": 7}
    assert est["per"]["c"] == {"pass": 2, "rework": 1, "total": 3}  # a custom charter counts 2
    assert est["per"]["v"]["total"] == 2


def test_the_total_is_the_sum_and_an_empty_team_costs_nothing() -> None:
    planner = BudgetPlanner()
    est = planner.estimate(TEAM)
    assert est["total"] == sum(v["total"] for v in est["per"].values()) == 7 + 4 + 3 + 3
    assert planner.estimate([]) == {"per": {}, "total": 0}


def test_the_task_names_its_budget_else_the_estimate_plus_slack_within_the_cap() -> None:
    planner = BudgetPlanner()
    assert planner.planned_total({"task": {"budget": 9}}, 17) == 9
    assert planner.planned_total({"task": {"budget": True}, "needs": {"budget_runs": 40}}, 17) == 22  # a bool is no number of runs
    assert planner.planned_total({}, 17) == 22
    assert planner.planned_total({"needs": {"budget_runs": 20}}, 17) == 20
    assert planner.planned_total({"needs": {"budget_runs": 0}}, 17) == 22 and planner.planned_total({"needs": {"budget_runs": "x"}}, 17) == 22


def test_each_child_is_granted_its_whole_subtree_and_the_parent_keeps_the_rest() -> None:
    split = BudgetPlanner().budget_split(TEAM, 22)
    assert split["lead"] == {"grant": 22, "keeps": 22 - 4 - 3 - 3}
    assert [split[a]["grant"] for a in ("lead/researcher", "lead/writer", "lead/check")] == [4, 3, 3]
    assert all(split[a]["keeps"] == split[a]["grant"] for a in ("lead/researcher", "lead/writer", "lead/check"))


def test_a_deeper_tree_hands_down_the_subtree_of_a_child() -> None:
    team = [agent("a", "manager", ("a/b",)), agent("a/b", "manager", ("a/b/c",)), agent("a/b/c", "author", runs=2)]
    split = BudgetPlanner().budget_split(team, 30)
    assert split["a/b"] == {"grant": 8, "keeps": 5} and split["a/b/c"] == {"grant": 3, "keeps": 3}
    assert split["a"] == {"grant": 30, "keeps": 22}


def test_a_service_costs_its_own_budget_else_the_estimate_plus_slack_within_the_cap() -> None:
    planner = BudgetPlanner()
    assert planner.service_budget({"budget": 7}, 17, 20, round_runs=0) == 7
    assert planner.service_budget({}, 17, 25, round_runs=0) == 22 and planner.service_budget({}, 17, 20, round_runs=0) == 20
    assert planner.service_budget({}, 17, None, round_runs=0) == 22
    assert planner.service_budget({"budget": True}, 17, 20, round_runs=0) == 20  # a bool is no number of runs


def test_the_client_round_is_one_run_plus_two_for_each_agent_below_the_owner() -> None:
    planner = BudgetPlanner()
    assert planner.client_round(TEAM) == 7  # lead, researcher, writer, check: 1 + 2 * 3
    assert planner.client_round([agent("lead", "manager", ("lead/w", "lead/r")), agent("lead/w", "author"), agent("lead/r", "verifier")]) == 5
    assert planner.client_round([agent("a", "manager", ("a/b",)), agent("a/b", "manager", ("a/b/c",)), agent("a/b/c", "author")]) == 5  # nested agents count
    assert planner.client_round([agent("solo", "manager")]) == 1  # an owner alone
    assert planner.client_round([]) == 0


def test_a_service_budget_covers_one_client_round_when_that_is_more_than_the_slack() -> None:
    """D-E5-2: the larger of the estimate plus 25% and the estimate plus one client round, within the cap."""
    planner = BudgetPlanner()
    assert planner.service_budget({}, 17, 25, round_runs=7) == 24  # 17 + 7 beats ceil(17 * 1.25) = 22
    assert planner.service_budget({}, 17, 20, round_runs=7) == 20  # the cap wins
    assert planner.service_budget({}, 11, 12, round_runs=5) == 12
    assert planner.service_budget({}, 11, None, round_runs=5) == 16
    assert planner.service_budget({}, 40, None, round_runs=7) == 50  # the slack is larger
    assert planner.service_budget({"budget": 7}, 17, 25, round_runs=7) == 7  # an explicit budget is kept


def test_every_service_of_the_blueprint_has_its_budget_by_name() -> None:
    bp = {"needs": {"budget_runs": 25}, "services": [{"name": "a", "budget": 9}, {"name": "b"}, "junk"]}
    assert BudgetPlanner().service_budgets(bp, TEAM) == {"a": 9, "b": 24}  # b: the estimate plus one client round, under the cap of 25
    assert BudgetPlanner().service_budgets(bp, []) == {"a": 9, "b": 0}


@pytest.mark.parametrize(("total", "est", "round_runs", "offer"), [
    (10, 11, 5, None), (11, 11, 5, 16), (12, 11, 5, 16), (15, 11, 5, 16), (16, 11, 5, None), (12, 11, 0, None),
])
def test_the_plans_number_is_offered_only_when_a_budget_covers_the_estimate_but_not_a_client_round(total: int, est: int, round_runs: int, offer: int | None) -> None:
    """D-E7-3: ``round_offer`` is the estimate plus one client round exactly where the ``budget-tight`` warning's client-round form fires."""
    assert round_offer(total, est, round_runs) == offer
