"""The budget slice of the ``Org`` facade: ``budget``, ``delegable``, ``grant_hint``, ``_check_allocation``, ``_default_budget``, ``_budget_to_return`` and
``reclaim`` behave as they always did (green before and after), and now go through the ports of the runtime (``budget_query``, ``allocation_policy``
and ``budget_reclaimer``)."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org
from orgmcp.budget import AllocationPolicy, BudgetQuery, BudgetReclaimer
from orgmcp.kernel import Message, OrgError


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_the_budget_is_what_was_received_minus_given_minus_runs(org: Org) -> None:
    assert org.budget("ceo") == 0 and org.budget("root") is None
    org.send("root", "ceo", "runs", budget=6)
    org.send("ceo", "ceo/eng", "runs", budget=2)
    org.start_run_log("ceo")
    assert (org.budget("ceo"), org.budget("ceo/eng")) == (3, 2)


def test_delegable_and_the_hint_of_an_agent_that_can_hire(org: Org) -> None:
    org.send("root", "ceo", "runs", budget=3)
    assert org.delegable("ceo") == (3, 0, 2)
    assert org.grant_hint("ceo") == "`ceo` now has 3 run(s) and 0 outstanding delegation(s); with one more delegation it can hand down at most 2 run(s)."
    assert org.grant_hint("ceo/eng") == "" and org.grant_hint("ghost") == ""


def test_the_private_helpers_of_dispatch_keep_their_names_and_rules(org: Org) -> None:
    org.send("root", "ceo", "runs", budget=6)
    org._check_allocation("ceo", 5, False)
    with pytest.raises(OrgError, match="not enough budget: you have 6 run"):
        org._check_allocation("ceo", 6, True)
    assert org._default_budget("ceo") == 5 and org._default_budget("root") == 10


def test_reclaim_moves_the_runs_back(org: Org) -> None:
    org.send("root", "ceo", "runs", budget=6)
    org.send("ceo", "ceo/eng", "runs", budget=3)
    org.begin_run("ceo/eng")
    org.end_run("ceo/eng", ok=True)
    assert org.reclaim("ceo", "eng", 2).budget == 2 and (org.budget("ceo"), org.budget("ceo/eng")) == (5, 1)


# -------------------------------------------------------------------------------------------- through the ports


class Fixed(BudgetQuery):
    def budget(self, addr: str) -> int | None:
        return 77

    def delegable(self, addr: str) -> tuple[int, int, int]:
        return 77, 1, 75

    def grant_hint(self, addr: str) -> str:
        return f"hint for {addr}"


class Policy(AllocationPolicy):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        self.calls.append(("check_allocation", actor, amount, new_delegation))

    def default_budget(self, actor: str) -> int:
        self.calls.append(("default_budget", actor))
        return 4

    def budget_to_return(self, actor: str, task: Message, status: str) -> int:
        self.calls.append(("budget_to_return", actor, task.id, status))
        return 3


class Reclaimer(BudgetReclaimer):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def reclaim(self, actor: str, report: str, budget: int | None = None) -> Message:
        self.calls.append((actor, report, budget))
        return Message(sender="x", to="y", type="note", body="reclaimed", id="FROM-THE-PORT")


def test_the_questions_come_from_the_budget_query_of_the_runtime(org: Org) -> None:
    use(org, budget_query=Fixed())
    assert org.budget("ceo") == 77 and org.delegable("ceo") == (77, 1, 75) and org.grant_hint("ceo") == "hint for ceo"


def test_the_rules_come_from_the_allocation_policy_of_the_runtime(org: Org) -> None:
    policy = Policy()
    use(org, allocation_policy=policy)
    org._check_allocation("ceo", 2, True)
    assert org._default_budget("ceo") == 4
    task = Message(sender="root", to="ceo", type="task", body="b", id="T1")
    assert org._budget_to_return("ceo", task, "done") == 3
    assert policy.calls == [("check_allocation", "ceo", 2, True), ("default_budget", "ceo"), ("budget_to_return", "ceo", "T1", "done")]


def test_reclaim_comes_from_the_reclaimer_of_the_runtime(org: Org) -> None:
    reclaimer = Reclaimer()
    use(org, budget_reclaimer=reclaimer)
    assert org.reclaim("ceo", "eng", 2).id == "FROM-THE-PORT" and org.reclaim("ceo", "eng").id == "FROM-THE-PORT"
    assert reclaimer.calls == [("ceo", "eng", 2), ("ceo", "eng", None)]


def test_what_the_dispatch_slice_hands_down_goes_through_the_policy(org: Org) -> None:
    policy = Policy()
    use(org, allocation_policy=policy)
    task = org.delegate("root", "ceo", "T", "g", "a")
    assert task.budget == 4 and ("default_budget", "root") in policy.calls
    org.delegate("ceo", "ceo/eng", "t", "g", "a", budget=1)
    assert ("check_allocation", "ceo", 1, True) in policy.calls
