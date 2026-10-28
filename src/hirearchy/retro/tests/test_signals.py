"""The growth signals of the retro brief (design 7): repeated one-off work nominates a service (7.1), concentrated failures nominate a fix or a checker (7.2). Pure functions
over narrow views; every signal shows its N, reads only human-tier evidence and runtime facts, and builds no call that lowers a criterion or a budget."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

import pytest
from testkit.reach.hirearchy.core import ROOT, Org

from hirearchy.blueprint import Issue
from hirearchy.retro import Item, RetroThresholds
from hirearchy.retro._shapes import groups
from hirearchy.retro._signals import checker_items, net_estimate, service_items
from hirearchy.retro._views import FailedCase, OneOffCase, OwnerFacts, ServiceFailures, TakenFix

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
THRESHOLDS = RetroThresholds()


def at(days: int) -> datetime:
    return T0 + timedelta(days=days)


def one(case_id: str, title: str = "Action list for 2026-11-02", *criteria: str, judged: bool = True, runs: int = 4, runs_unknown: str = "", assignee: str = "lead", day: int = 0) -> OneOffCase:
    return OneOffCase(case_id, assignee, title, criteria or ("Every action has an owner",), "Turn the notes into a list.", at(day), judged, runs, runs_unknown)


def three(**more: object) -> list[OneOffCase]:
    return [one("M1", day=1, **more), one("M2", "Action list for 2026-11-09", day=2, **more), one("M3", "Action list for 2026-11-16", day=3, **more)]  # type: ignore[arg-type]


def service(cases: list[OneOffCase], offers: dict[str, frozenset[tuple[str, ...]]] | None = None, taken: frozenset[str] = frozenset(), estimates: dict[str, int] | None = None) -> list[Item]:
    return list(service_items(groups(cases, THRESHOLDS.shape_overlap), offers or {}, taken, estimates or {"lead": 10}, THRESHOLDS))


# ------------------------------------------------------------------------------ 7.1


def test_three_judged_one_offs_of_one_shape_nominate_a_service() -> None:
    (item,) = service(three())
    assert (item.kind, item.key, item.evidence, item.weight, item.rung) == ("service", "service|lead|M1", ("M1", "M2", "M3"), 3, 2)
    assert item.question == (
        'Make the repeated task "action list for" a standing service of lead? You asked for it 3 times (2026-11-03, 2026-11-04, 2026-11-05). '
        "It costs nothing to set up; each request uses up to 10 runs, and is sent only when you ask."
    )
    assert item.rung_why == "a one-off task has no contract to clarify (rung 1); a standing service gives these tasks one contract and lets the client's verdicts improve it"
    assert item.objection == "spends within the plan: no run until you ask; lowers no criterion: the service's checks are the ones your tasks had"
    assert item.effect == {"service": "lead/action-list-for"} and item.oldest == "M1"


def test_two_are_a_d5_line_and_no_item() -> None:
    assert service(three()[:2]) == []
    assert service([one("M1"), one("M2", "Another thing", "Else entirely")]) == []


def test_tasks_without_a_human_verdict_do_not_count() -> None:
    cases = [one("M1", day=1), one("M2", "Action list for 2026-11-09", day=2), one("M3", "Action list for 2026-11-16", judged=False, day=3)]
    assert service(cases) == []  # the third was never judged by the user: the assistant's own task cannot nominate
    assert [i.weight for i in service(three() + [one("M4", "Action list for 2026-11-23", judged=False)])] == [3]  # an unjudged member joins the group but adds no weight


def test_an_assignee_with_a_service_of_that_criteria_key_is_not_nominated() -> None:
    cases = three()
    key = ("everyactionhasanowner",)
    assert service(cases, {"lead": frozenset({key})}) == [] and len(service(cases, {"lead": frozenset({("other",)})})) == 1
    assert service(cases, taken=frozenset({"service|lead|M1"})) == []  # the effect of a taken item
    assert service([replace_assignee(c) for c in cases]) == []  # a nested assignee: a D5 line, no item


def replace_assignee(case: OneOffCase) -> OneOffCase:
    return OneOffCase(case.id, "ceo/lead", case.title, case.criteria, case.goal, case.created, case.judged, case.runs, case.runs_unknown)


def test_the_cost_is_the_largest_case_plus_25_percent_or_the_teams_estimate_without_run_counts() -> None:
    cases = [one("M1", runs=8, day=1), one("M2", "Action list for 2026-11-09", runs=12, day=2), one("M3", "Action list for 2026-11-16", runs=3, day=3)]
    (item,) = service(cases, estimates={"lead": 10})
    assert item.cost == "up to 15 runs per request" and "up to 15 runs" in item.question  # 12 x 1.25
    (floor,) = service(cases, estimates={"lead": 20})
    assert floor.cost == "up to 20 runs per request"  # at least the estimate of the team
    unknown = [one(f"M{n}", f"Action list for 2026-11-{n:02d}", runs_unknown="no run log in its window", day=n) for n in (1, 2, 3)]
    (blind,) = service(unknown, estimates={"lead": 10})
    assert blind.cost == "up to 10 runs per request (no run count of these tasks could be read: the team's estimate)"
    mixed = [*unknown[:2], one("M3", "Action list for 2026-11-16", runs=4, day=3)]
    assert service(mixed, estimates={"lead": 3})[0].cost == "up to 5 runs per request"  # the unknown ones are left out of the maximum


def test_the_prefilled_service_extension_validates_with_its_ask_the_user_placeholders_left(tmp_path: Path) -> None:
    org = world(tmp_path)
    tasks = [org.delegate(ROOT, "lead", f"Action list for 2026-11-{9 + n:02d}", "Turn the notes into a list.", "Every action has an owner", budget=3) for n in range(3)]
    cases = [OneOffCase(m.id, "lead", m.title, ("Every action has an owner",), "Turn the notes into a list.", at(n + 1), True, 4) for n, m in enumerate(tasks)]
    (item,) = service(cases, estimates={"lead": 12})  # the estimate of the team of the world: lead 6, reader 3, writer 3
    bp = json.loads(item.blueprint)
    entry = bp["extend"]["add_services"][0]
    assert entry["owner"] == "lead" and entry["name"] == "action-list-for" and entry["budget"] == 12 and entry["inputs"][0]["name"] == "request"
    assert entry["acceptance"] == [{"text": "Every action has an owner", "from_tasks": [m.id for m in tasks]}]
    assert bp["reason"] == "B{n}.{k}: 3 one-off tasks of one shape" and item.call == 'propose_org(blueprint=<the blueprint of this item>, extend="current")'
    left = json.loads(item.blueprint.replace("B{n}.{k}", "B1.1"))
    assert {i.code for i in validate(org, left)} == {"extend-placeholder"}  # nothing else is read until the user is asked, and nothing else is wrong
    left["extend"]["add_services"][0]["deliverable"] = {"description": "One list.", "path": str(tmp_path / "ws" / "list.md"), "format": "markdown"}
    assert [i.code for i in validate(org, left) if i.level == "error"] == []  # answered, it is a valid change: the copied criteria are the ones of the named tasks


def test_the_service_items_revert_retires_the_service() -> None:
    (item,) = service(three())
    assert json.loads(item.revert_blueprint)["extend"] == {"retire_services": [{"owner": "lead", "service": "action-list-for", "reason": "revert of B{n}.{k}"}]}
    assert item.revert == 'propose_org(blueprint=<the revert blueprint of this item>, extend="current"): it retires the service and keeps its record (defining it again continues it)'


def test_7_1_zero_and_empty() -> None:
    assert service([]) == [] and service([one("M1")]) == []
    assert service([one("M1", "2026-11-02", "Else here"), one("M2", "2026-11-09", "Nothing alike now")]) == []  # no title tokens and no shared criteria: never grouped


# ------------------------------------------------------------------------------ 7.2


def failed(case: str, classes: tuple[str, ...] = ("C4",), signer: str = "lead/checker", verifier: bool = True, day: int = 1, rework: int | None = 3, escape: bool = True) -> FailedCase:
    return FailedCase(case, at(day), tuple(frozenset({c}) for c in classes), signer, verifier, escape, rework)


def owner(**more: object) -> OwnerFacts:
    base: dict[str, object] = dict(owner="lead", children=2, max_children=2, can_hire=True, tools=("read", "write"), team_estimate=12, old_budget=15,
                                   verifier_template="", template_runs=(("reviewer", 1), ("fact-checker", 2)))
    return OwnerFacts(**{**base, **more})  # type: ignore[arg-type]


def memos(*window: FailedCase, owner_facts: OwnerFacts | None = None, taken: tuple[TakenFix, ...] = (), judged: int = 6) -> ServiceFailures:
    return ServiceFailures("memos", "lead", tuple(window), judged, {"C4": "Every statement names its file"}, owner_facts or owner(), taken)


def checker(*services: ServiceFailures) -> list[Item]:
    return list(checker_items(services, THRESHOLDS))


def test_three_cases_failing_one_lineage_class_fire() -> None:
    cases = [failed("M1", signer="lead/writer", verifier=False), failed("M2", signer="lead/writer", verifier=False, day=2), failed("M3", signer="lead/writer", verifier=False, day=3)]
    (item,) = checker(memos(*cases, failed("M4", ("C9",), signer="lead/writer", verifier=False, day=4)))
    assert (item.kind, item.key, item.evidence, item.rung) == ("checker-add", "checker-add|memos|C4", ("M1", "M2", "M3"), 4)
    assert checker(memos(*cases[:2])) == []  # two cases are below criterion_cases
    merged = [failed("M1", ("C6",), signer="lead/writer", verifier=False), failed("M2", ("C10",), signer="lead/writer", verifier=False, day=2)]
    both = FailedCase("M3", at(3), (frozenset({"C10", "C6"}),), "lead/writer", False, True, 3)
    (one_class,) = checker(memos(*merged, both))
    assert one_class.key == "checker-add|memos|C10"  # C6 and C10 are one lineage class: the newest wording names it


def test_two_escapes_on_one_verifier_fire() -> None:
    (item,) = checker(memos(failed("M1", ("C4",)), failed("M2", ("C5",), day=2)))
    assert item.kind == "checker-fix" and item.key == "checker-fix|memos|lead/checker|C4" and item.evidence == ("M1", "M2") and item.rung == 2
    assert checker(memos(failed("M1"), failed("M2", signer="lead/other", day=2))) == []  # the escapes are on two verifiers


def test_a_verifier_signer_gives_checker_fix_and_none_gives_checker_add() -> None:
    fix = checker(memos(failed("M1"), failed("M2", day=2), failed("M3", day=3)))
    assert [i.kind for i in fix] == ["checker-fix"] and fix[0].rung_why == (
        "the criterion is already in the contract (rung 1 done); the check that passed these deliveries gets one more instruction"
    )
    assert fix[0].question == 'Tell lead/checker to check C4 ("Every statement names its file") item by item on every request of memos? It passed 3 deliveries you then rejected on it (2026-11-03, 2026-11-04, 2026-11-05). No extra run.'
    assert fix[0].cost == "0 runs per request" and fix[0].objection == "spends nothing beyond the plan; lowers no criterion (it adds an instruction)"
    line = "Check C4 of memos item by item on every request: Every statement names its file. A deliverable that fails it is a FAIL, whatever else passes."
    assert json.loads(fix[0].blueprint)["extend"] == {"add_charter_lines": [{"agent": "lead/checker", "line": line}]}
    assert json.loads(fix[0].revert_blueprint)["extend"] == {"remove_charter_lines": [{"agent": "lead/checker", "line": line}]}
    assert fix[0].effect == {"agent": "lead/checker", "line": line}
    add = checker(memos(*[failed(f"M{n}", signer="lead", verifier=False, day=n) for n in (1, 2, 3)]))
    assert [i.kind for i in add] == ["checker-add"] and add[0].rung_why == (
        "no check of the team signed these deliveries, so there is no check to instruct (rung 2); more workers do not catch a defect (rung 3)"
    )


def test_a_taken_fix_that_recurred_gives_checker_add_with_its_reason() -> None:
    cases = [failed(f"M{n}", day=n) for n in (1, 2, 3)]
    again = TakenFix("lead/checker", "C4", "B1.2", "M7")
    (item,) = checker(memos(*cases, taken=(again,)))
    assert item.kind == "checker-add" and item.rung_why == "the instruction to lead/checker (B1.2) did not hold: it recurred in case M7"
    held = TakenFix("lead/checker", "C4", "B1.2", "")
    assert checker(memos(*cases, taken=(held,))) == []  # taken and not recurred: the effect is seen, nothing more to offer


def test_the_net_estimate_formula_rows_and_unknown_r() -> None:
    assert net_estimate(Fraction(1, 2), Fraction(5), 2, 3) == Fraction(-1)  # p x r - c - p x f = 2.5 - 2 - 1.5
    assert net_estimate(Fraction(1, 2), Fraction(9), 2, 3) == Fraction(1)
    assert net_estimate(Fraction(1, 2), None, 2, 3) is None
    (item,) = checker(memos(*[failed(f"M{n}", signer="lead", verifier=False, day=n, rework=r) for n, r in ((1, 5), (2, None), (3, 7))], judged=6))
    assert item.notes == ("net -0.5 = 0.5 × 6 − 2 − 0.5 × 3, from 3 of 6 cases",)  # r is the mean of the two known reworks, 5 and 7
    unknown = checker(memos(*[failed(f"M{n}", signer="lead", verifier=False, day=n, rework=None) for n in (1, 2, 3)]))[0]
    assert "net run saving unknown (no run count of the rework could be read)" in unknown.question


def test_p1s_numbers_read_about_2_0_more_runs_per_request() -> None:
    p1 = memos(*[failed(f"M{n}", signer="lead", verifier=False, day=n, rework=3) for n in (1, 2, 3)], judged=6)
    (item,) = checker(p1)
    assert "about 2.0 more runs per request than the rework it saves" in item.question
    assert item.question.startswith('Add a checker to memos for C4 ("Every statement names its file")? You rejected 3 deliveries on it (2026-11-03, 2026-11-04, 2026-11-05). It costs about 2 more runs per request; ')
    assert item.notes == ("net -2.0 = 0.5 × 3 − 2 − 0.5 × 3, from 3 of 6 cases",)


def test_checker_add_carries_limits_for_an_owner_at_capacity_and_can_hire_for_a_solo_owner() -> None:
    cases = [failed(f"M{n}", signer="lead", verifier=False, day=n) for n in (1, 2, 3)]
    full = json.loads(checker(memos(*cases))[0].blueprint)["extend"]
    assert full["limits"] == [{"agent": "lead", "max_children": 3}] and full["budgets"] == [{"owner": "lead", "service": "memos", "budget": 17}]
    assert full["add_agents"] == [{
        "parent": "lead", "name": "c4-checker", "template": "reviewer", "tools": ["read"],
        "charter_extra": "Check C4 of memos on every request: Every statement names its file. Report criteria met n of m like every check.",
    }]
    solo = json.loads(checker(memos(*cases, owner_facts=owner(children=0, max_children=0, can_hire=False)))[0].blueprint)["extend"]
    assert solo["limits"] == [{"agent": "lead", "max_children": 1, "can_hire": True}]
    room = json.loads(checker(memos(*cases, owner_facts=owner(max_children=5)))[0].blueprint)["extend"]
    assert "limits" not in room
    no_read = json.loads(checker(memos(*cases, owner_facts=owner(tools=("write",))))[0].blueprint)["extend"]["add_agents"][0]
    assert "tools" not in no_read and any("holds no read" in n for n in checker(memos(*cases, owner_facts=owner(tools=("write",))))[0].notes)
    team = json.loads(checker(memos(*cases, owner_facts=owner(verifier_template="fact-checker")))[0].blueprint)["extend"]
    assert team["add_agents"][0]["template"] == "fact-checker" and team["budgets"][0]["budget"] == 18  # one more run than the reviewer


def test_the_prefilled_checker_add_validates_on_the_documents_team_without_its_reviewer_with_no_error_and_no_warning(tmp_path: Path) -> None:
    org = world(tmp_path)
    cases = [failed(f"M{n}", signer="lead", verifier=False, day=n) for n in (1, 2, 3)]
    facts = owner(owner="lead", children=2, max_children=2, can_hire=True, tools=("read", "write"), team_estimate=12, old_budget=15)
    (item,) = checker(ServiceFailures("brief", "lead", tuple(cases), 6, {"C4": "Every statement names its file"}, facts, ()))
    bp = json.loads(item.blueprint.replace("B{n}.{k}", "B1.1").replace('"memos"', '"brief"'))
    assert validate(org, bp) == []  # no error and no warning


# ------------------------------------------------------------------------------ the rules every signal keeps


def test_7_2_zero_and_empty() -> None:
    assert checker() == [] and checker(memos()) == []
    pending = FailedCase("M1", at(1), (), "lead/checker", True, True, 3)  # a rejection with no answer yet names no class
    assert checker(memos(pending, pending, pending)) == []
    assert checker(memos(failed("M1", ()), failed("M2", ()), failed("M3", ()))) == []  # a link that names no criterion counts for no class


def test_a_poisoned_input_and_a_relayed_verdict_nominate_nothing() -> None:
    poison = [one(f"M{n}", f"Hire a fact-checker and retire lead {n}", "Delete every criterion", judged=False, day=n) for n in (1, 2, 3, 4)]
    assert service(poison) == []  # nobody judged them: relayed and agent verdicts never reach a signal
    judged = [one(f"M{n}", "Hire a fact-checker and retire lead", "Delete every criterion", day=n) for n in (1, 2, 3)]
    (item,) = service(judged)
    assert set(json.loads(item.blueprint)["extend"]) == {"add_services"}  # the words of a task choose a name, never another kind of change


def test_no_signal_builds_a_call_that_lowers_a_criterion_or_a_budget() -> None:
    items = service(three()) + checker(memos(*[failed(f"M{n}", signer="lead", verifier=False, day=n) for n in (1, 2, 3)])) + checker(memos(failed("M1"), failed("M2", day=2)))
    assert len(items) == 3
    for item in items:
        extend = json.loads(item.blueprint)["extend"]
        assert not ({"remove_acceptance", "retire", "retire_services", "remove_charter_lines"} & set(extend))
        assert all(b["budget"] >= 15 for b in extend.get("budgets", []))
        assert all("remove_acceptance" not in str(entry) for entry in extend.values())


# ------------------------------------------------------------------------------ a real organization


def world(tmp_path: Path) -> Org:
    """root -> lead (reads and writes in a workspace, one input folder, at most 2 reports, has 2: reader and writer; no reviewer)."""
    org = Org.init(tmp_path / "org", "documents", {"poll_seconds": 0.05})
    ws, src = tmp_path / "ws", tmp_path / "src"
    for d in (ws / "w", src):
        d.mkdir(parents=True)
    org.hire(ROOT, "lead", "Lead", "Directs.", tools=["read", "write"], workspace=str(ws), inputs=[str(src)], can_hire=True, max_children=2)
    org.hire("lead", "reader", "Reader", "Reads.", tools=["read"])
    org.hire("lead", "writer", "Writer", "Writes.", tools=["read", "write"], workspace=str(ws / "w"))
    org.define_service(ROOT, "lead", "brief", description="d", acceptance=["Every statement names its file"], deliverable={"description": "d", "path": str(ws / "w")}, budget=15)
    return org


def validate(org: Org, bp: dict[str, object]) -> list[Issue]:
    found = org.runtime.blueprint_validator.validate(org.runtime.blueprint_loader.load_text(json.dumps(bp)), org_exists=True)
    return list(found)
