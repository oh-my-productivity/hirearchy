"""``CharterWriter``: the charter of every agent of the example blueprints is the one the flat module wrote."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint._charters import CharterWriter
from hirearchy.blueprint._shapes import Split
from hirearchy.blueprint.api import Agent, Role
from hirearchy.blueprint.testing import role_library_of, StaticOrgContext
from hirearchy.kernel.testing import DictEnvironment

from ._plans import LABELS, base_dir, golden, load_text, scrub, template_at
from ._support import role


def agents_of(label: str, tmp: Path) -> tuple[dict[str, object], list[Agent], dict[str, Split], Path]:
    from hirearchy.blueprint._budgeting import BudgetPlanner
    from hirearchy.blueprint._pathcheck import RootedPathChecker
    from hirearchy.blueprint._resolver import AgentResolver

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


def test_the_extension_charter_has_the_users_change_heading() -> None:
    reviewer = Agent("lead/checker", "checker", "lead", "extend.add_agents[0]", role="Independent Reviewer", template=role("reviewer", title="Independent Reviewer", kind="verifier", body="# Role: Reviewer"),
                     kind="verifier", tools=["read"], inputs=["/data/in"])
    text = CharterWriter().extension_charter(reviewer, [], "abc123def456", "Check every date.")
    assert text == (
        "# Role: Reviewer\n\n## Assignment (from the user's change abc123def456)\nReports to: lead\n"
        "Read-only inputs: /data/in. Read them (kiro `read`, or hirearchy `read` by absolute path); never create, edit or delete anything there.\n\n"
        "## Additional instructions\nCheck every date."
    )
    lead = Agent("team", "team", None, "extend.add_agents[0]", role="Lead", template=role("manager", title="Manager", kind="manager", body="# Role: Manager"), kind="manager",
                 children=["team/a"])
    worker = Agent("team/a", "a", "team", "extend.add_agents[0]", role="Writer", kind="author", tools=["write"], model="claude-sonnet-5.5")
    body = CharterWriter().extension_charter(lead, [worker], "p1", "")
    assert "Reports to: root (the human)" in body and "- team/a: Writer (author; tools: write; model: claude-sonnet-5.5)" in body and "Additional" not in body
    custom = Agent("solo", "solo", None, "w", role="Solo", extra="You work alone.", kind="author")
    assert CharterWriter().extension_charter(custom, [], "p2", "").startswith("You work alone.\n\n## Assignment (from the user's change p2)")
