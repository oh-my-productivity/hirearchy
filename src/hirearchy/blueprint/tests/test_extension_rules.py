"""The rules of an extension blueprint (design 5.1 and 5.2): its form (``extend-form``, ``extend-placeholder``, ``extend-keeps``) and, in the next
commits, its entries read against the organization. The form needs no organization: the resolver reads none to judge it."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint import Issue, is_extension
from hirearchy.blueprint._extension import ExtensionResolver
from hirearchy.blueprint.testing import StaticOrgContext


def resolve(bp: dict[str, object], tmp: Path | None = None) -> list[Issue]:
    return ExtensionResolver(StaticOrgContext(tmp)).resolve(bp).issues


def extension(**sections: object) -> dict[str, object]:
    return {"reason": "B1.1: checks", "extend": dict(sections)}


LIMITS = [{"agent": "lead", "max_children": 3}]


def codes(issues: list[Issue]) -> list[str]:
    return [i.code for i in issues]


def test_is_extension_reads_the_top_level_extend_key() -> None:
    assert is_extension({"extend": {"limits": LIMITS}}) and is_extension({"reason": "r", "extend": None}) and is_extension({"extend": {}})
    assert not is_extension({"mission": "m", "agents": []}) and not is_extension({"needs": {"extend": 1}}) and not is_extension("extend:")
    assert not is_extension(None)


def test_a_well_formed_extension_has_no_form_issue() -> None:
    assert resolve(extension(limits=LIMITS)) == []


@pytest.mark.parametrize("empty", [None, {}, {"limits": []}, {"retire": []}])
def test_an_empty_extend_is_extend_form(empty: object) -> None:
    issues = resolve({"reason": "r", "extend": empty})
    assert codes(issues) == ["extend-form"] and issues[0].level == "error" and "no entry" in issues[0].message or "mapping" in issues[0].message


def test_an_unknown_or_a_non_list_section_is_extend_form() -> None:
    unknown = resolve(extension(limits=LIMITS, add_robots=[{"name": "x"}]))
    assert codes(unknown) == ["extend-form"] and "add_robots" in unknown[0].message and "add_agents" in unknown[0].message
    not_a_list = resolve(extension(limits={"agent": "lead", "max_children": 3}))
    assert codes(not_a_list) == ["extend-form"] and "extend.limits" in not_a_list[0].path
    not_a_mapping = resolve(extension(limits=["lead"]))
    assert codes(not_a_mapping) == ["extend-form"] and not_a_mapping[0].path == "extend.limits[0]"
    assert codes(resolve({"reason": "r", "extend": ["limits"]})) == ["extend-form"]
    assert codes(resolve({"reason": "r", "extend": "limits"})) == ["extend-form"]


def test_an_unknown_key_of_an_entry_is_extend_form_naming_the_known_ones() -> None:
    issues = resolve(extension(limits=[{"agent": "lead", "max_kids": 3}]))
    assert codes(issues) == ["extend-form"] and "max_kids" in issues[0].message and "max_children" in issues[0].message


@pytest.mark.parametrize("key", ["mission", "agents", "task", "services", "whatever"])
def test_mission_or_agents_in_an_extension_is_extend_form(key: str) -> None:
    issues = resolve({**extension(limits=LIMITS), key: "x"})
    assert codes(issues) == ["extend-form"] and issues[0].path == key and "extend" in issues[0].message


def test_a_reason_is_required_one_line_of_at_most_300_characters() -> None:
    for reason in (None, "", "   ", "two\nlines", 7):
        issues = resolve({"extend": {"limits": LIMITS}, **({} if reason is None else {"reason": reason})})
        assert codes(issues) == ["extend-form"] and issues[0].path == "reason"
    assert resolve({"reason": "x" * 300, "extend": {"limits": LIMITS}}) == []


def test_needs_may_hold_only_elicitation_and_budget_runs() -> None:
    assert resolve({**extension(limits=LIMITS), "needs": {"elicitation": "their words", "budget_runs": 30}}) == []
    issues = resolve({**extension(limits=LIMITS), "needs": {"scope": "all", "deliverable": "x"}})
    assert codes(issues) == ["extend-form", "extend-form"] and {i.path for i in issues} == {"needs.scope", "needs.deliverable"}
    assert codes(resolve({**extension(limits=LIMITS), "needs": "words"})) == ["extend-form"]


@pytest.mark.parametrize("where", ["reason", "line", "charter_extra", "reason_of_retire"])
def test_an_unreplaced_placeholder_is_extend_placeholder(where: str) -> None:
    text = "<ASK THE USER: which folder?>"
    bp: dict[str, object] = {
        "reason": text if where == "reason" else "r",
        "extend": {
            "add_charter_lines": [{"agent": "lead", "line": text if where == "line" else "Check everything."}],
            "add_agents": [{"parent": "lead", "name": "checker", "template": "reviewer", "charter_extra": text if where == "charter_extra" else "ok"}],
            "retire": [{"agent": "old", "reason": text if where == "reason_of_retire" else "done"}],
        },
    }
    issues = resolve(bp)
    assert codes(issues) == ["extend-placeholder"] and "<ASK THE USER: which folder?>" in issues[0].message
    assert resolve({"reason": "a < b and c > d", "extend": {"limits": LIMITS}}) == []  # a comparison is no placeholder


KEEPS = [
    ("budgets", {"owner": "lead", "service": "weekly", "acceptance": ["x"]}, "the criteria of weekly", "they change only with the user's words", "define_service(owner, name, add_acceptance=..., words="),
    ("budgets", {"owner": "lead", "service": "weekly", "add_acceptance": ["x"]}, "the criteria of weekly", "words", "define_service"),
    ("budgets", {"owner": "lead", "service": "weekly", "playbook": "steps"}, "the playbook of weekly", "the owner keeps it", "revise_playbook"),
    ("limits", {"agent": "lead/writer", "tools": ["write"]}, "the tools of lead/writer", "an existing agent's tools are the plan it was approved with", "Add a new agent with those tools, or change them at the terminal"),
    ("limits", {"agent": "lead/writer", "model": "claude-opus-5.5"}, "the model of lead/writer", "an existing agent's model is the plan it was approved with", "Add a new agent with those model"),
    ("limits", {"agent": "lead/writer", "workspace": "/x"}, "the workspace of lead/writer", "the plan it was approved with", "change them at the terminal"),
    ("add_charter_lines", {"agent": "lead/writer", "line": "x", "inputs": ["/x"]}, "the inputs of lead/writer", "an existing agent's inputs are the plan it was approved with", "Add a new agent"),
    ("limits", {"agent": "lead", "charter": "new text"}, "the charter of lead", "an existing charter changes only through its added section", "add_charter_lines"),
    ("remove_charter_lines", {"agent": "lead", "line": "x", "body": "new"}, "the charter of lead", "added section", "remove_charter_lines"),
    ("limits", {"org": "default_model", "value": 3}, "the ORG.md setting default_model", "ORG.md's rules and settings are the user's, except max_depth", "max_depth"),
    ("limits", {"agent": "lead", "budget": 9}, "the budget of lead", "spend is handed down with send(budget=N)", "send(to, ..., budget=N)"),
    ("budgets", {"agent": "lead", "budget": 9}, "the budget of lead", "send(budget=N)", "budgets changes the per-request budget"),
]


@pytest.mark.parametrize(("section", "entry", "what", "why", "how"), KEEPS)
def test_each_forbidden_change_is_extend_keeps_with_its_what_why_how(section: str, entry: dict[str, object], what: str, why: str, how: str) -> None:
    issues = resolve(extension(**{section: [entry]}))
    assert codes(issues) == ["extend-keeps"] and issues[0].level == "error" and issues[0].path == f"extend.{section}[0]"
    assert issues[0].message.startswith(f"an extension cannot change {what}: ") and why in issues[0].message and how in issues[0].message


def test_the_keys_an_added_agent_or_service_names_are_its_own_and_forbidden_nowhere() -> None:
    bp = extension(
        add_agents=[{"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"], "model": "strong", "workspace": "/w", "inputs": ["/i"],
                     "role": "Checker", "charter_extra": "x"}],
        add_services=[{"owner": "lead", "name": "weekly", "description": "d", "acceptance": ["a"], "deliverable": "x", "budget": 5, "playbook": "p"}],
    )
    assert resolve(bp) == []


def test_at_most_20_entries_per_section_and_300_characters_of_reason() -> None:
    twenty = [{"agent": f"a{i}", "max_children": 2} for i in range(20)]
    assert resolve(extension(limits=twenty)) == []
    issues = resolve(extension(limits=[*twenty, {"agent": "b", "max_children": 2}]))
    assert codes(issues) == ["extend-form"] and "21 entries" in issues[0].message and "at most 20" in issues[0].message
    long = resolve({"reason": "x" * 301, "extend": {"limits": LIMITS}})
    assert codes(long) == ["extend-form"] and long[0].path == "reason"


def test_schedules_are_not_part_of_this_version() -> None:
    issues = resolve(extension(schedules=[{"owner": "lead", "service": "weekly"}]))
    assert codes(issues) == ["extend-form"] and "schedules" in issues[0].message
