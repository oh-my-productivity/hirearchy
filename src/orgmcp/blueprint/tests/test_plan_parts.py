"""The small parts of the plan side: the basis (problems and agents of a blueprint) and the words about services."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.blueprint._protocols import PlanBasis, PlanWords
from orgmcp.blueprint._words import ServiceWords
from orgmcp.blueprint.api import Agent
from orgmcp.blueprint.testing import StaticOrgContext, plan_parts_over, role_library_of
from orgmcp.kernel.testing import DictEnvironment
from orgmcp.services.testing import normalizer

from ._plans import base_dir, load_text, template_at


def basis_over(tmp: Path, org: StaticOrgContext) -> PlanBasis:
    parts = plan_parts_over(role_library_of(packaged=True), org, environment=DictEnvironment(home=tmp, cwd=tmp), temp_dir=tmp / "temp")
    return parts.basis


def test_the_issues_are_the_problems_of_the_blueprint_and_names_taken_count_only_when_the_organization_exists(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    bp = load_text(template_at("research", "filled", base))
    without = basis_over(tmp_path, StaticOrgContext(root=None, agents=["lead"]))
    present = basis_over(tmp_path, StaticOrgContext(root=tmp_path / "org", agents=["lead"]))
    assert "exists" not in {i.code for i in without.issues(bp, [base])}
    assert "exists" in {i.code for i in present.issues(bp, [base])}


def test_the_agents_are_the_resolved_ones_parents_first(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    agents = basis_over(tmp_path, StaticOrgContext()).agents(load_text(template_at("research", "filled", base)), [base])
    assert [a.addr for a in agents] == ["lead", "lead/researcher", "lead/writer", "lead/factcheck"] and agents[0].parent is None
    assert all(isinstance(a, Agent) and a.model for a in agents)


def test_the_agents_of_a_blueprint_with_problems_are_those_that_can_be_resolved(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    bp = load_text(template_at("research", "filled", base))
    cast(list[dict[str, object]], cast(list[dict[str, object]], bp["agents"])[0]["children"])[0]["template"] = "wizard"
    agents = basis_over(tmp_path, StaticOrgContext()).agents(bp, [base])
    assert [a.addr for a in agents] == ["lead", "lead/researcher", "lead/writer", "lead/factcheck"]  # (the problem is told by the issues, not by dropping the agent)


# ------------------------------------------------------------------------------------------------ words


@pytest.fixture
def words(tmp_path: Path) -> PlanWords:
    made = ServiceWords(normalizer(tmp_path))
    assert isinstance(made, PlanWords)
    return made


def test_inputs_in_words(words: PlanWords) -> None:
    sv = {"inputs": [{"name": "topic", "description": "t", "required": True}, {"name": "week", "description": "w", "required": False}]}
    assert words.input_words(sv) == "topic (required), week (optional)"
    assert words.input_words({}) == "nothing: every request is the same"
    assert words.input_words({"inputs": "not a list"}) == "(see the errors)"


def test_the_first_request_in_words_clips_each_value(words: PlanWords) -> None:
    bp = {"task": {"service": "s", "inputs": {"topic": "ai chips", "empty": "", "long": "word " * 40}}}
    assert words.request_words(bp) == "topic: ai chips, long: " + ("word " * 40).strip()  # (a lone sentence is never cut)
    assert words.request_words({}) == ""


def test_the_reflection_line_names_the_lead_unless_it_is_called_lead(words: PlanWords) -> None:
    assert words.reflection_line("lead").startswith("After each request the lead records lessons; before the next one it reviews them")
    assert words.reflection_line("boss").startswith("After each request the lead (boss) records lessons;")
    assert words.reflection_line("lead").endswith("It cannot change these checks: only you can, through me.")


def agent(addr: str, tools: list[str], workspace: str | None, kind: str = "author") -> Agent:
    return Agent(addr=addr, name=addr, parent=None, where="x", kind=kind, tools=tools, workspace=workspace)


def test_where_a_service_is_delivered(words: PlanWords, tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    out = tmp_path / "ws" / "out"
    author = agent("w", ["write", "shell"], str(ws))
    bp: dict[str, object] = {"needs": {}}
    assert words.delivery({}, [author], bp) == "inside the organization folder (no location given)"
    assert words.delivery({"deliverable": {"path": str(out)}}, [author], bp) == f"{out} (the team writes it there)"
    assert words.delivery({"deliverable": {"path": str(out)}}, [agent("w", ["write"], str(ws))], bp) == f"{out} (I copy each result there after checking it)"
    code = {"needs": {"workspace": str(ws), "kind": "code"}}
    assert words.delivery({}, [author], code) == f"the workspace {ws} (the team works and commits there)"


# ------------------------------------------------------------------------------------------------ the words about access


def test_what_an_agent_may_touch_in_plain_words(tmp_path: Path) -> None:
    from orgmcp.blueprint._accesswords import PlainAccessWords
    from orgmcp.blueprint._protocols import AccessWording
    from orgmcp.blueprint.testing import ScriptedConfinementPolicy, access_over

    open_org = {"read": {"allowedPaths": ["/orgmcp-org-root", "/orgmcp-org-root/**"], "deniedPaths": []}}
    words = PlainAccessWords(access_over(ScriptedConfinementPolicy(open_org)))
    assert isinstance(words, AccessWording)
    assert words.describe(agent("w", ["write"], "/ws")) == "changes files only in /ws"
    assert words.describe(agent("w", ["web_search", "web_fetch"], None)) == "can search the web and read web pages; cannot change your files"
    assert words.describe(agent("m", ["read"], "/ws", kind="manager")).startswith("directs the team; does not produce the work itself; can read files only in /ws")
    assert words.describe(agent("s", ["shell"], None)).startswith("can run commands, which are NOT confined: it is told to stay in its own folder, but nothing enforces that")
