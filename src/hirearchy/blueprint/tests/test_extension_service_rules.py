"""The rules of an extension that concern services and charter lines (design 5.1, 5.2): ``add_services``, ``budgets``, ``retire_services`` and the lines."""

from __future__ import annotations

from pathlib import Path

import pytest
from testkit.reach.hirearchy.core import ROOT

from ._extension_world import World, codes, extension, world

CRITERIA = ["Every row has a date.", "At most 3 pages."]


@pytest.fixture
def w(tmp_path: Path) -> World:
    """lead (writer under it) offers `weekly` at 9 runs per request; solo offers nothing."""
    made = world(tmp_path)
    made.org.define_service(
        ROOT, "lead", "weekly", description="A weekly note", inputs=[], acceptance=CRITERIA, deliverable={"description": "a note"}, budget=9, playbook="steps",
    )
    return made


def service(name: str = "monthly", owner: str = "solo", **over: object) -> dict[str, object]:
    return {
        "owner": owner, "name": name, "description": "A monthly note", "acceptance": [{"text": "Every row has a date.", "default": True}],
        "deliverable": {"description": "a note"}, **over,
    }


def errors(w: World, **sections: object) -> list[str]:
    return codes(w.errors(extension(**sections)))


def test_a_valid_service_resolves_with_its_budget_for_the_owners_team(w: World) -> None:
    ext = w.resolver.resolve(extension(add_services=[service()]), allowed_roots=[w.tmp])
    assert [i.code for i in ext.issues if i.level == "error"] == []
    (added,) = ext.services
    assert (added.owner, added.name, added.where, added.continues) == ("solo", "monthly", "extend.add_services[0]", None)
    assert added.budget == 4  # a solo owner's estimate is 3 (a pass of 2 and a rework of 1); with the slack and one client round: 4
    assert [a.addr for a in ext.teams["solo"]] == ["solo"]


def test_extend_owner_needs_a_top_level_agent_and_a_free_name(w: World) -> None:
    for owner in ("ghost", "lead/writer", ROOT, ""):
        issues = w.errors(extension(add_services=[service(owner=owner)]))
        assert codes(issues) == ["extend-owner"] and issues[0].path == "extend.add_services[0]"
    assert "top-level" in w.errors(extension(add_services=[service(owner="lead/writer")]))[0].message
    assert errors(w, add_services=[service("Bad Name")]) == ["extend-owner"]
    assert errors(w, add_services=[service("twice"), service("twice", "lead")]) == ["extend-owner"]
    taken_elsewhere = w.errors(extension(add_services=[service("weekly", "solo")]))
    assert codes(taken_elsewhere) == ["service-name"] and "already exists" in taken_elsewhere[0].message
    own = w.errors(extension(add_services=[service("weekly", "lead")]))
    assert codes(own) == ["extend-keeps"] and "an extension cannot change the criteria of weekly" in own[0].message


def test_a_continuation_repeats_the_retired_criteria_or_is_extend_owner(w: World) -> None:
    w = w.using(continued={("solo", "monthly"): ["At most 3 pages.", "Every row has a date."]})
    repeated = service(acceptance=[{"text": "Every row has a date.", "default": True}, {"text": "At most 3 pages.", "default": True}])
    assert w.errors(extension(add_services=[repeated])) == []  # in any order, with their sources
    ext = w.resolver.resolve(extension(add_services=[repeated]), allowed_roots=[w.tmp])
    assert ext.services[0].continues == ("At most 3 pages.", "Every row has a date.")
    other = w.errors(extension(add_services=[service()]))  # one of the two criteria
    assert codes(other) == ["extend-owner"]
    assert other[0].message == (
        'monthly continues the retired service of solo, so its criteria are the retired ones: "At most 3 pages."; "Every row has a date.". '
        "Repeat them (each with its source), or pick another name."
    )
    assert codes(w.errors(extension(add_services=[{**repeated, "playbook": "new steps"}]))) == ["extend-owner"]  # a continuation keeps its playbook


def test_extend_service_applies_todays_service_rules(w: World) -> None:
    for broken, code in (({"description": ""}, "service"), ({"acceptance": []}, "criteria"), ({"deliverable": {}}, "deliverable"), ({"budget": 0}, "service"),
                         ({"inputs": "no good"}, "service-inputs"), ({"budget": 1}, "budget-low")):
        found = w.errors(extension(add_services=[service(**broken)]))
        assert codes(found) == [code], (broken, found)
        assert found[0].path.startswith("extend.add_services[0]")
    capped = {**extension(add_services=[service(budget=50)]), "needs": {"budget_runs": 20}}
    assert codes(w.errors(capped)) == ["budget-cap"]
    vague = w.issues(extension(add_services=[service(acceptance=[{"text": "Be good and professional.", "default": True}])]), level="warning")
    assert "vague-criterion" in codes(vague)


def test_a_verifier_added_without_raising_the_budget_is_extend_budget(tmp_path: Path) -> None:
    w = world(tmp_path, lead_reports=4)
    w.org.define_service(ROOT, "lead", "weekly", description="d", inputs=[], acceptance=CRITERIA, deliverable={"description": "x"}, budget=6, playbook="s")
    checker = {"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"]}
    low = w.errors(extension(add_agents=[checker]))
    assert codes(low) == ["extend-budget"] and "weekly of lead runs on 6 runs per request" in low[0].message and "needs at least" in low[0].message
    est = int(low[0].message.split("needs at least ")[1].split(":")[0])
    assert low[0].message.endswith(f"[{{owner: lead, service: weekly, budget: {est}}}] to this change (the user sees the new budget in the plan).")
    assert w.errors(extension(add_agents=[checker], budgets=[{"owner": "lead", "service": "weekly", "budget": est}])) == []


def test_extend_budget_rules(w: World) -> None:
    def bad(*entries: dict[str, object], needs: dict[str, object] | None = None) -> list[str]:
        bp = extension(budgets=list(entries))
        return codes(w.errors({**bp, "needs": needs} if needs else bp))

    assert bad({"owner": "lead", "service": "weekly", "budget": 12}) == []
    assert bad({"owner": "lead", "service": "nothing", "budget": 12}) == ["extend-budget"] and bad({"owner": "ghost", "service": "weekly", "budget": 12}) == ["extend-budget"]
    assert bad({"owner": "lead", "service": "weekly", "budget": 0}) == ["extend-budget"] and bad({"owner": "lead", "service": "weekly", "budget": "9"}) == ["extend-budget"]
    assert bad({"owner": "lead", "service": "weekly", "budget": 9}) == ["extend-budget"]  # as it is
    assert bad({"owner": "lead", "service": "weekly", "budget": 1}) == ["extend-budget"]  # below the estimate of its team
    assert bad({"owner": "lead", "service": "weekly", "budget": 30}, needs={"budget_runs": 20}) == ["extend-budget"]
    assert bad({"owner": "lead", "service": "weekly", "budget": 12}, {"owner": "lead", "service": "weekly", "budget": 13}) == ["extend-budget"]
    assert codes(w.errors({**extension(budgets=[{"owner": "lead", "service": "weekly", "budget": 12}]), "needs": {"budget_runs": 0}})) == ["extend-form"]
    ext = w.resolver.resolve(extension(budgets=[{"owner": "lead", "service": "weekly", "budget": 12}]), allowed_roots=[w.tmp])
    assert [(b.owner, b.service, b.budget, b.was) for b in ext.budgets] == [("lead", "weekly", 12, 9)]


def test_extend_retire_service_needs_settled_cases(w: World) -> None:
    retire = [{"owner": "lead", "service": "weekly", "reason": "not used"}]
    assert w.errors(extension(retire_services=retire)) == []
    ext = w.resolver.resolve(extension(retire_services=retire), allowed_roots=[w.tmp])
    assert [(r.owner, r.service, r.reason) for r in ext.service_retires] == [("lead", "weekly", "not used")]
    assert errors(w, retire_services=[*retire, *retire]) == ["extend-retire-service"]  # twice
    task = w.org.request(ROOT, "weekly", {}, title="one")
    w.org.report("lead", task.id, "done", "ready", lessons="Nothing new.")
    open_ = w.errors(extension(retire_services=retire))
    assert codes(open_) == ["extend-retire-service"]
    assert open_[0].message == "weekly still has 1 delivered request(s) with no verdict yet: settle them first, then propose this change again"
    for bad in ({"owner": "lead", "service": "nothing", "reason": "x"}, {"owner": "solo", "service": "weekly", "reason": "x"}, {"owner": "lead", "service": "weekly", "reason": ""}):
        assert errors(w, retire_services=[bad]) == ["extend-retire-service"]


def test_extend_line_rules(w: World) -> None:
    def bad(line: object, agent: str = "lead") -> list[str]:
        return errors(w, add_charter_lines=[{"agent": agent, "line": line}])

    assert bad("Check every date.") == []
    ext = w.resolver.resolve(extension(add_charter_lines=[{"agent": "lead/writer", "line": "  Cite   the   source.  "}]), allowed_roots=[w.tmp])
    assert [(c.agent, c.line) for c in ext.lines] == [("lead/writer", "Cite the source.")]
    assert bad("x" * 300) == [] and bad("x" * 301) == ["extend-line"] and bad("") == ["extend-line"] and bad(5) == ["extend-line"]
    assert bad("two\nlines") == ["extend-line"] and bad("# A heading") == ["extend-line"] and bad("--- frontmatter") == ["extend-line"]
    assert bad("sneaky [change abc123]") == ["extend-line"]
    assert bad("ok", "ghost") == ["extend-line"] and bad("ok", ROOT) == ["extend-line"] and bad("ok", "") == ["extend-line"]
    twice = errors(w, add_charter_lines=[{"agent": "lead", "line": "Same."}, {"agent": "lead", "line": "same"}])
    assert twice == ["extend-line"]
    assert errors(w, add_charter_lines=[{"agent": "lead", "line": "Same."}, {"agent": "solo", "line": "Same."}]) == []


def test_remove_charter_lines_names_only_a_line_of_the_added_section(w: World) -> None:
    def remove(line: str, agent: str = "lead") -> list[str]:
        return errors(w, remove_charter_lines=[{"agent": agent, "line": line}])

    assert remove("Check every date.") == ["extend-line"]  # no added section yet
    meta, body = w.org.charter("lead")
    from hirearchy.kernel import join_frontmatter

    w.org.runtime.agent_registry.rewrite_charter("lead", join_frontmatter(meta, body + "\n\n## Added by your changes\n- Check every date. [change abc123def456]\n"))
    assert remove("check every date") == [] and remove("  Check every date.  ") == []
    assert remove("Directs.") == ["extend-line"]  # a line of the charter, not of the added section
    assert errors(w, add_charter_lines=[{"agent": "lead", "line": "Check every date."}]) == ["extend-line"]  # it has it already
    ext = w.resolver.resolve(extension(remove_charter_lines=[{"agent": "lead", "line": "CHECK every date!"}]), allowed_roots=[w.tmp])
    assert [(c.agent, c.line) for c in ext.removals] == [("lead", "Check every date.")]  # the line as it was added, without its tag
    assert errors(w, remove_charter_lines=[{"agent": "lead", "line": "Check every date."}, {"agent": "lead", "line": "check every date"}]) == ["extend-line"]


def test_a_verifier_added_under_an_agent_that_offers_services_is_a_checker_of_them(w: World) -> None:
    ext = w.resolver.resolve(
        extension(add_agents=[{"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"]}], limits=[{"agent": "lead", "max_children": 3}],
                  budgets=[{"owner": "lead", "service": "weekly", "budget": 14}]),
        allowed_roots=[w.tmp],
    )
    assert [(c.agent, c.owner, c.services) for c in ext.checkers] == [("lead/checker", "lead", ("weekly",))]
    assert [i.code for i in ext.issues if i.level == "error"] == []
    none = w.resolver.resolve(extension(add_agents=[{"parent": "solo", "name": "c2", "template": "reviewer", "tools": ["read"]}],
                                        limits=[{"agent": "solo", "can_hire": True, "max_children": 1}]), allowed_roots=[w.tmp])
    assert none.checkers == []  # solo offers no service


def test_the_added_agents_join_the_team_the_services_are_budgeted_for(w: World) -> None:
    ext = w.resolver.resolve(
        extension(add_agents=[{"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"]}], limits=[{"agent": "lead", "max_children": 3}],
                  budgets=[{"owner": "lead", "service": "weekly", "budget": 14}]), allowed_roots=[w.tmp],
    )
    assert [a.addr for a in ext.teams["lead"]] == ["lead", "lead/writer", "lead/checker"]
    gone = w.resolver.resolve(extension(retire=[{"agent": "lead/writer", "reason": "x"}]), allowed_roots=[w.tmp])
    assert [a.addr for a in gone.teams["lead"]] == ["lead"]
