"""The rules of an extension that read the organization (design 5.2): the agents it adds, the limits it changes and the agents it retires."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from hirearchy.blueprint._extension import ExtensionResolver
from hirearchy.blueprint._org import NoOrgContext
from testkit.reach.hirearchy.core import ROOT

from ._extension_world import World, codes, extension, reads_of, world


@pytest.fixture
def w(tmp_path: Path) -> World:
    return world(tmp_path)


def checker(parent: str = "lead", name: str = "checker", **over: object) -> dict[str, object]:
    return {"parent": parent, "name": name, "template": "reviewer", "tools": ["read"], **over}


def test_a_valid_checker_under_the_lead_resolves_to_an_agent_with_its_parents_inputs(w: World) -> None:
    ext = w.resolver.resolve(extension(add_agents=[checker()], limits=[{"agent": "lead", "max_children": 3}]), allowed_roots=[w.tmp])
    assert [i for i in ext.issues if i.level == "error"] == []
    (agent,) = ext.agents
    assert (agent.addr, agent.parent, agent.kind, agent.role) == ("lead/checker", "lead", "verifier", "Independent Reviewer")
    assert agent.inputs[0] == str(w.tmp / "src") and agent.tools == ["read"] and agent.model == "claude-sonnet-5.5"


def test_no_organization_is_extend_none(w: World) -> None:
    bare = ExtensionResolver(replace(reads_of(w.org), org=NoOrgContext()))
    found = bare.resolve(extension(limits=[{"agent": "lead", "max_children": 3}])).issues
    assert [(i.code, i.level) for i in found] == [("extend-none", "error")]
    assert found[0].message == (
        "refused: there is no organization yet, so there is nothing to extend: create_org(mission=...) and a full blueprint come first."
    )


def test_a_parent_must_exist_and_not_be_retired(w: World) -> None:
    w.org.hire("lead", "gone", "Gone", "x", tools=["read"])
    w.org.retire(ROOT, "lead/gone", "not needed")
    for parent in ("ghost", "lead/gone", "lead/writer/none"):
        issues = w.errors(extension(add_agents=[checker(parent)]))
        assert codes(issues) == ["extend-parent"] and parent in issues[0].message and issues[0].path == "extend.add_agents[0]"
    assert codes(w.errors(extension(add_agents=[{"name": "x", "template": "reviewer"}]))) == ["extend-parent"]
    assert w.errors(extension(add_agents=[checker(ROOT, "newteam", tools=[])])) == []  # under root: a new team


def test_a_new_address_must_be_free_and_a_retired_address_may_be_used_again(w: World) -> None:
    taken = w.errors(extension(add_agents=[checker("lead", "writer")], limits=[{"agent": "lead", "max_children": 3}]))
    assert codes(taken) == ["extend-name"] and "lead/writer already exists" in taken[0].message
    twice = w.errors(extension(add_agents=[checker(), checker()], limits=[{"agent": "lead", "max_children": 4}]))
    assert codes(twice) == ["extend-name"] and "in this change too" in twice[0].message
    w.org.retire(ROOT, "solo", "done")
    assert w.errors(extension(add_agents=[checker(ROOT, "solo", tools=[])])) == []  # the address of a retired agent is free again
    bad = w.errors(extension(add_agents=[checker("lead", "Bad Name")], limits=[{"agent": "lead", "max_children": 3}]))
    assert codes(bad) == ["name"]


def test_depth_is_checked_against_the_extensions_own_max_depth(tmp_path: Path) -> None:
    w = world(tmp_path, max_depth=2)
    deep = checker("lead/writer", "helper", tools=["read"])
    refused = w.errors(extension(add_agents=[deep], limits=[{"agent": "lead/writer", "can_hire": True, "max_children": 1}]))
    assert "extend-depth" in codes(refused) and "depth 3" in next(i.message for i in refused if i.code == "extend-depth")
    allowed = w.errors(extension(add_agents=[deep], limits=[{"agent": "lead/writer", "can_hire": True, "max_children": 1}, {"org": "max_depth", "value": 3}]))
    assert allowed == []  # limits are applied before the additions: the extension's own max_depth is the one that counts


def test_a_parent_at_capacity_is_extend_capacity_with_the_limits_to_add(w: World) -> None:
    w.org.hire("lead", "second", "Second", "x", tools=["read"])  # the lead has 2 of 2 reports
    issues = w.errors(extension(add_agents=[checker()]))
    assert codes(issues) == ["extend-capacity"]
    assert issues[0].message == (
        "lead may have 2 direct reports and has 2; this change adds 1. Add limits: [{agent: lead, max_children: 3}] to this change "
        "(the user sees it in the plan)."
    )
    solo = w.errors(extension(add_agents=[checker("solo", "c2")]))
    assert codes(solo) == ["extend-capacity"] and solo[0].message == (
        "solo may have 0 direct reports and has 0; this change adds 1. Add limits: [{agent: solo, max_children: 1, can_hire: true}] to this change "
        "(the user sees it in the plan)."
    )


def test_the_extensions_own_limits_entry_frees_the_place(w: World) -> None:
    w.org.hire("lead", "second", "Second", "x", tools=["read"])
    assert w.errors(extension(add_agents=[checker()], limits=[{"agent": "lead", "max_children": 3}])) == []
    assert w.errors(extension(add_agents=[checker("solo", "c2")], limits=[{"agent": "solo", "max_children": 1, "can_hire": True}])) == []
    assert codes(w.errors(extension(add_agents=[checker("solo", "c2")], limits=[{"agent": "solo", "max_children": 1}]))) == ["extend-capacity"]


def test_retires_of_the_same_extension_free_no_place(w: World) -> None:
    w.org.hire("lead", "second", "Second", "x", tools=["read"])
    issues = w.errors(extension(add_agents=[checker()], retire=[{"agent": "lead/second", "reason": "unused"}]))
    assert codes(issues) == ["extend-capacity"]  # the retire is applied last: the place is not free when the hire happens


def test_tools_workspace_and_inputs_only_narrow_under_a_non_root_parent(w: World) -> None:
    free = [{"agent": "lead", "max_children": 4}]
    tools = w.errors(extension(add_agents=[checker(tools=["web_search"])], limits=free))
    assert codes(tools) == ["extend-tools"] and "web_search" in tools[0].message and "lead" in tools[0].message
    outside = w.errors(extension(add_agents=[checker(workspace=str(w.tmp / "elsewhere"), tools=["read"]), checker(name="c2", workspace=str(w.tmp / "ws" / "w"))], limits=free))
    assert "extend-workspace" in codes(outside)
    (w.tmp / "elsewhere").mkdir()
    assert codes(w.errors(extension(add_agents=[checker(workspace=str(w.tmp / "elsewhere"))], limits=free))) == ["extend-workspace"]
    assert w.errors(extension(add_agents=[checker(workspace=str(w.tmp / "ws" / "w"), tools=["read"])], limits=free)) == []
    (w.tmp / "other-src").mkdir()
    refused = w.errors(extension(add_agents=[checker(inputs=[str(w.tmp / "other-src")])], limits=free))
    assert codes(refused) == ["extend-inputs"] and "other-src" in refused[0].message
    assert w.errors(extension(add_agents=[checker(inputs=[str(w.tmp / "src")])], limits=free)) == []
    under_root = checker(ROOT, "team", tools=["web_search", "web_fetch"], workspace=str(w.tmp / "elsewhere"))
    assert w.errors(extension(add_agents=[under_root])) == []  # under root nothing narrows: the user's own plan


def test_an_added_agent_inherits_its_parents_inputs_and_a_verifier_also_the_siblings_workspaces(w: World) -> None:
    more = [{"agent": "lead", "max_children": 3}]
    ext = w.resolver.resolve(extension(add_agents=[checker()], limits=more), allowed_roots=[w.tmp])
    (agent,) = ext.agents
    assert agent.inputs == [str(w.tmp / "src"), str(w.tmp / "ws" / "w")]  # the parent's input, then the workspace of the writer the lead holds
    assert [i.code for i in ext.issues] == []
    own = w.resolver.resolve(extension(add_agents=[checker(inputs=[str(w.tmp / "src")])], limits=more), allowed_roots=[w.tmp])
    assert own.agents[0].inputs == [str(w.tmp / "src")]  # an explicit list is the extension's own decision, which the reader is warned about
    assert [(i.level, i.code) for i in own.issues] == [("warning", "verifier-cannot-read")]
    worker = w.resolver.resolve(extension(add_agents=[checker(name="helper", template="writer", tools=["read"])], limits=more), allowed_roots=[w.tmp])
    assert worker.agents[0].inputs == [str(w.tmp / "src")]  # an author gets its parent's inputs only
    bare = w.resolver.resolve(extension(add_agents=[checker("solo", "c2", tools=["read"], inputs=[])], limits=[{"agent": "solo", "can_hire": True, "max_children": 1}]),
                              allowed_roots=[w.tmp])
    assert "read-nothing" in codes(bare.issues)


def test_extend_limit_rules(w: World) -> None:
    def bad(*entries: dict[str, object]) -> list[str]:
        return codes(w.errors(extension(limits=list(entries))))

    assert w.errors(extension(limits=[{"agent": "lead", "max_children": 5}, {"agent": "solo", "can_hire": True, "max_children": 2}, {"org": "max_depth", "value": 6}])) == []
    assert bad({"agent": "ghost", "max_children": 3}) == ["extend-limit"]
    assert bad({"agent": ROOT, "max_children": 3}) == ["extend-limit"]
    assert bad({"agent": "lead"}) == ["extend-limit"]  # nothing to change
    assert bad({"agent": "lead", "max_children": 0}) == ["extend-limit"]  # below its one report now
    assert bad({"agent": "lead", "max_children": "many"}) == ["extend-limit"]
    assert bad({"agent": "lead", "can_hire": "yes"}) == ["extend-limit"]
    assert bad({"agent": "lead", "can_hire": False}) == ["extend-limit"]  # it has a report
    assert bad({"agent": "lead", "max_children": 2, "can_hire": True}) == ["extend-limit"]  # as it is
    assert bad({"agent": "lead", "max_children": 3}, {"agent": "lead", "max_children": 4}) == ["extend-limit"]
    assert bad({"org": "max_depth", "value": 0}) == ["extend-limit"] and bad({"org": "max_depth", "value": 1}) == ["extend-limit"]  # the writer is at depth 2
    assert bad({"org": "max_depth", "value": 4}) == ["extend-limit"]  # as it is
    assert bad({"org": "max_depth", "value": 5}, {"org": "max_depth", "value": 6}) == ["extend-limit"]
    ext = w.resolver.resolve(extension(limits=[{"agent": "lead", "max_children": 5}, {"org": "max_depth", "value": 6}]), allowed_roots=[w.tmp])
    assert [(c.agent, c.can_hire, c.max_children, c.was_can_hire, c.was_max_children) for c in ext.limits] == [("lead", None, 5, True, 2)]
    assert (ext.depth.value, ext.depth.was) == (6, 4) if ext.depth else False


def test_extend_retire_rules_and_an_agent_named_by_another_entry(w: World) -> None:
    def bad(*entries: dict[str, object], **more: object) -> list[str]:
        return codes(w.errors(extension(retire=list(entries), **more)))

    assert bad({"agent": "lead/writer", "reason": "not needed"}) == []
    assert bad({"agent": "ghost", "reason": "x"}) == ["extend-retire"] and bad({"agent": ROOT, "reason": "x"}) == ["extend-retire"]
    assert bad({"agent": "solo", "reason": ""}) == ["extend-retire"] and bad({"agent": "solo", "reason": "x" * 301}) == ["extend-retire"]
    assert bad({"agent": "solo", "reason": "x"}, {"agent": "solo", "reason": "y"}) == ["extend-retire"]
    assert bad({"agent": "lead", "reason": "x"}, {"agent": "lead/writer", "reason": "y"}) == ["extend-retire"]  # the team once
    named = bad({"agent": "lead", "reason": "x"}, limits=[{"agent": "lead/writer", "can_hire": True, "max_children": 1}])
    assert named == ["extend-retire"]  # it names a member of the team that goes
    assert bad({"agent": "lead/writer", "reason": "x"}, add_agents=[checker()]) == []  # a sibling is not named
    msg = w.errors(extension(retire=[{"agent": "solo", "reason": "x"}], add_agents=[checker("solo", "c2")]))
    assert any("retire it in a later change" in i.message for i in msg)
    ext = w.resolver.resolve(extension(retire=[{"agent": "lead", "reason": "done"}]), allowed_roots=[w.tmp])
    assert [(r.agent, r.team) for r in ext.retires] == [("lead", ("lead", "lead/writer"))]


def test_retiring_the_last_verifier_of_a_service_team_is_an_extend_lowers_warning(tmp_path: Path) -> None:
    w = world(tmp_path, lead_reports=4)
    w.org.hire("lead", "checker", "Independent Reviewer", "Checks.", tools=["read"])
    w.org.define_service(
        ROOT, "lead", "weekly", description="d", inputs=[], acceptance=["Every row has a date."], deliverable={"description": "x"}, budget=9, playbook="steps",
    )
    retire = [{"agent": "lead/checker", "reason": "too slow"}]
    warned = w.issues(extension(retire=retire), level="warning")
    assert [(i.code, i.message) for i in warned] == [("extend-lowers", "this removes the last check of weekly: its requests are then checked only by lead")]
    assert w.errors(extension(retire=retire)) == []
    other = w.issues(extension(retire=retire, add_agents=[checker(name="second")], limits=[{"agent": "lead", "max_children": 5}]), level="warning")
    assert "extend-lowers" not in codes(other)  # the extension adds a check in its place
    w.org.hire("lead", "checker2", "Independent Reviewer", "Checks.", tools=["read"])
    assert codes(w.issues(extension(retire=retire), level="warning")) == []  # another check stays
    assert codes(w.issues(extension(retire=[{"agent": "lead", "reason": "all"}]), level="warning")) == []  # the service goes with the team
