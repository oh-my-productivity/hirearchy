"""``CharterWriter``: the charter of every agent of the example blueprints is the one the flat module wrote."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.blueprint._charters import CharterWriter
from orgmcp.blueprint._shapes import Split
from orgmcp.blueprint.api import Agent, Role
from orgmcp.blueprint.testing import plan_parts_over, role_library_of, StaticOrgContext
from orgmcp.kernel.testing import DictEnvironment

from ._plans import LABELS, base_dir, golden, load_text, scrub, template_at
from ._support import role


def agents_of(label: str, tmp: Path) -> tuple[dict[str, object], list[Agent], dict[str, Split], Path]:
    from orgmcp.blueprint._budgeting import BudgetPlanner
    from orgmcp.blueprint._pathcheck import RootedPathChecker
    from orgmcp.blueprint._resolver import AgentResolver

    base = base_dir(tmp)
    bp = load_text(template_at(label, "filled", base))
    environment = DictEnvironment(home=tmp, cwd=tmp)
    agents = AgentResolver(role_library_of(packaged=True), RootedPathChecker(environment)).resolve(bp, StaticOrgContext(), [base], [])
    budgets = BudgetPlanner()
    split = budgets.budget_split(agents, budgets.planned_total(bp, budgets.estimate(agents)["total"]))
    return bp, agents, split, base


@pytest.mark.parametrize("label", LABELS)
def test_every_charter_is_the_text_the_flat_module_wrote(label: str, tmp_path: Path) -> None:
    bp, agents, split, base = agents_of(label, tmp_path)
    writer = CharterWriter()
    assert {a.addr: scrub(writer.charter(a, agents, bp, split), base) for a in agents} == golden()["charters"][label]


def test_a_charter_without_a_template_is_the_assignment_then_the_instructions() -> None:
    a = Agent(addr="solo", name="solo", parent=None, where="agents[solo]", role="Solo", kind="author", extra="Do it.", tools=["read"], model="m")
    text = CharterWriter().charter(a, [a], {"mission": "Be useful."}, {"solo": {"grant": 3, "keeps": 3}})
    assert text == "## Assignment (from the approved plan)\nMission: Be useful.\nReports to: root (the human)\n\nDo it."


def test_a_template_charter_comes_first_and_the_extra_text_gets_a_heading() -> None:
    template: Role = role("writer", body="You write.")
    a = Agent(addr="w", name="w", parent=None, where="agents[w]", role="Writer", template=template, extra="Extra.", model="m")
    text = CharterWriter().charter(a, [a], {"mission": "M"}, {"w": {"grant": 1, "keeps": 1}})
    assert text.startswith("You write.\n\n## Assignment (from the approved plan)\nMission: M") and text.endswith("\n\n## Additional instructions\nExtra.")
