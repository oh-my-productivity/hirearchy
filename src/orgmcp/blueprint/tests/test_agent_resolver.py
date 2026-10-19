"""``AgentResolver``: the agents of a blueprint, flattened parents first, with tools, workspace, inputs, authority and model settled."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from orgmcp.blueprint._protocols import AgentResolution
from orgmcp.blueprint._resolver import AgentResolver, declared_inputs, input_entries, review_roots
from orgmcp.blueprint.api import Agent, Issue
from orgmcp.blueprint.testing import MemoryRoleLibrary, StaticOrgContext, paths_over, role_library_of
from orgmcp.kernel.testing import DictEnvironment

from ._support import role



class World:
    def __init__(self, tmp: Path, roles: MemoryRoleLibrary | None = None) -> None:
        self.tmp = tmp
        self.resolver = AgentResolver(roles or role_library_of(packaged=False), paths_over(DictEnvironment(home=tmp, cwd=tmp)))
        self.issues: list[Issue] = []

    def resolve(self, bp: dict[str, object], org: StaticOrgContext | None = None) -> dict[str, Agent]:
        return {a.addr: a for a in self.resolver.resolve(bp, org or StaticOrgContext(), [self.tmp], self.issues)}

    def codes(self) -> list[str]:
        return [i.code for i in self.issues]


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def team(**lead: object) -> dict[str, object]:
    return {"mission": "m", "needs": {}, "agents": [{"name": "lead", "template": "manager", **lead, "children": [
        {"name": "writer", "template": "writer"}, {"name": "check", "template": "reviewer"}]}]}


def test_it_is_an_agent_resolution(tmp_path: Path) -> None:
    assert isinstance(World(tmp_path).resolver, AgentResolution)


def test_the_agents_come_parents_first_with_their_addresses_and_children(world: World) -> None:
    agents = world.resolve(team())
    assert list(agents) == ["lead", "lead/writer", "lead/check"]
    assert agents["lead"].children == ["lead/writer", "lead/check"] and agents["lead"].parent is None
    assert agents["lead/writer"].parent == "lead" and agents["lead/writer"].where == "agents[lead/writer]"
    assert world.issues == []


def test_the_blueprint_is_not_changed(world: World) -> None:
    bp = team()
    before = copy.deepcopy(bp)
    world.resolve(bp)
    assert bp == before


def test_kind_and_role_come_from_the_template_and_a_custom_charter_is_a_manager_only_with_a_team(world: World) -> None:
    agents = world.resolve({"agents": [{"name": "lead", "charter": "Lead it.", "children": [{"name": "solo", "charter": "Do it.", "role": "Doer"}]}]})
    assert (agents["lead"].kind, agents["lead/solo"].kind) == ("manager", "author")
    assert (agents["lead"].role, agents["lead/solo"].role) == ("lead", "Doer") and agents["lead"].template is None
    templates = world.resolve(team())
    assert templates["lead/check"].kind == "verifier" and templates["lead/check"].template is not None and templates["lead/writer"].role == "Writer"


def test_a_template_that_is_not_there_is_named_with_the_ones_that_are(tmp_path: Path) -> None:
    world = World(tmp_path, MemoryRoleLibrary([role("writer"), role("analyst")]))
    world.resolve({"agents": [{"name": "lead", "template": "wizard"}]})
    assert world.issues == [Issue("error", "agents[lead]", "unknown template 'wizard'; available: analyst, writer", "template")]


def test_an_agent_needs_a_template_or_a_charter(world: World) -> None:
    world.resolve({"agents": [{"name": "lead"}]})
    assert world.codes() == ["template"] and "give a template" in world.issues[0].message


@pytest.mark.parametrize("agents, code", [
    ("lead", "agents"), (["lead"], "agents"), ([{"name": "Bad Name", "template": "writer"}], "name"), ([{"name": "root", "template": "writer"}], "name"),
    ([{"name": "a", "template": "writer"}, {"name": "a", "template": "writer"}], "name"),
])
def test_what_cannot_be_an_agent_is_reported_and_skipped(world: World, agents: object, code: str) -> None:
    resolved = world.resolve({"agents": agents})
    assert world.codes() == [code] and len(resolved) <= 1


def test_scale_is_a_whole_number_from_one(world: World) -> None:
    for value, scale, bad in [(3, 3, False), (0, 1, True), ("2", 1, True), (None, 1, False)]:
        world.issues.clear()
        bp: dict[str, object] = {"agents": [{"name": "lead", "template": "manager", "scale": value}]} if value is not None else {"agents": [{"name": "lead", "template": "manager"}]}
        assert world.resolve(bp)["lead"].scale == scale and (world.codes() == ["scale"]) == bad


def test_tools_are_explicit_else_the_templates_and_a_manager_holds_what_it_hands_down(world: World) -> None:
    agents = world.resolve({"agents": [{"name": "lead", "template": "manager", "children": [
        {"name": "w", "template": "writer", "tools": "read, web_fetch"}, {"name": "c", "template": "reviewer"}]}]})
    assert agents["lead/w"].tools == ["read", "web_fetch"]
    assert agents["lead"].tools == sorted(set(agents["lead/w"].tools) | set(agents["lead/c"].tools))


def test_the_model_is_explicit_then_the_tier_then_the_default_of_the_organization(world: World) -> None:
    needs = {"models": {"cheap": "m-cheap", "strong": "m-strong"}}
    agents = world.resolve({"needs": needs, "agents": [{"name": "lead", "template": "manager", "model": "strong", "children": [
        {"name": "w", "template": "writer"}, {"name": "c", "template": "reviewer", "model": "claude-x"}]}]})
    assert (agents["lead"].model, agents["lead"].tier) == ("m-strong", "strong")
    assert agents["lead/w"].model == "m-cheap" and agents["lead/c"].model == "claude-x"
    defaults = world.resolve(team(), StaticOrgContext(config={"default_model": "org-default"}))
    assert {a.model for a in defaults.values()} == {"org-default"}


def test_children_beyond_max_children_and_a_bad_limit_are_reported_by_the_resolver_or_the_validator(world: World) -> None:
    world.resolve(team(max_children=-1))
    assert world.codes() == ["children"]


def test_a_writer_with_shell_gets_the_project_workspace_and_a_verifier_reads_it(world: World, tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    bp: dict[str, object] = {"needs": {"workspace": str(ws)}, "agents": [{"name": "lead", "template": "manager", "children": [
        {"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"}]}]}
    agents = world.resolve(bp)
    assert agents["lead/dev"].workspace == str(ws) and agents["lead"].workspace == str(ws)
    assert str(ws) in agents["lead/qa"].inputs or agents["lead/qa"].workspace == str(ws)


def test_inputs_must_exist_and_are_held_by_the_agents_that_read(world: World, tmp_path: Path) -> None:
    (tmp_path / "notes").mkdir()
    bp: dict[str, object] = {"needs": {"inputs": [str(tmp_path / "notes"), str(tmp_path / "missing")]}, "agents": [{"name": "lead", "template": "manager", "children": [
        {"name": "w", "template": "writer", "tools": ["read"]}]}]}
    agents = world.resolve(bp)
    assert agents["lead/w"].inputs == [str(tmp_path / "notes")] and agents["lead"].inputs == agents["lead/w"].inputs
    assert world.codes() == ["inputs"] and "does not exist" in world.issues[0].message


def test_a_path_that_fails_the_checks_is_reported_once_and_not_used(world: World) -> None:
    agents = world.resolve({"agents": [{"name": "w", "template": "writer", "workspace": "relative/ws"}]})
    assert world.codes() == ["path"] and agents["w"].workspace is None


def test_the_entries_of_an_inputs_list() -> None:
    issues: list[Issue] = []
    assert input_entries(None, "w", issues) == [] and input_entries("/a", "w", issues) == [("/a", False)]
    assert input_entries([" /a ", {"path": "/b", "allow_overlap": True}, {"path": "/c", "allow_overlap": "yes"}], "w", issues) == [
        ("/a", False), ("/b", True), ("/c", False)]
    assert issues == []
    assert input_entries(7, "w", issues) == [] and [i.code for i in issues] == ["inputs"]
    assert input_entries(["", 3], "w", issues) == [] and [i.code for i in issues] == ["inputs", "inputs", "inputs"]


def test_every_input_the_blueprint_names_with_where_it_was_named() -> None:
    bp = {"needs": {"inputs": ["/n"]}, "agents": [{"name": "lead", "inputs": ["/l"], "children": [
        {"name": "w", "inputs": [{"path": "/w", "allow_overlap": True}]}, "junk", {"name": "x"}]}]}
    assert declared_inputs(bp) == [("needs.inputs", "/n", False), ("agents[lead]", "/l", False), ("agents[lead/w]", "/w", True)]
    assert declared_inputs({}) == []


def test_the_review_roots_are_the_project_and_the_workspaces_of_authors_who_write() -> None:
    def a(addr: str, kind: str, tools: list[str], ws: str | None) -> Agent:
        return Agent(addr, addr, None, addr, kind=kind, tools=tools, workspace=ws)
    agents = [a("m", "manager", ["write", "shell"], "/p"), a("w1", "author", ["write", "shell"], "/p/a"), a("w2", "author", ["read"], "/p/b"),
              a("w3", "author", ["shell"], "/p/a"), a("v", "verifier", ["write"], "/p/v")]
    assert review_roots(agents, Path("/p")) == [Path("/p"), Path("/p/a")]
    assert review_roots(agents, None) == [Path("/p/a")]
