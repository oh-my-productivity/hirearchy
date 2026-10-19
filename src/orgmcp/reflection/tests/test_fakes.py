"""``FixedCaseHistory``: the cases a test puts in."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmcp.kernel import Message
from orgmcp.reflection import Case, CaseHistory
from orgmcp.reflection.testing import FixedCaseHistory

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def task(id: str) -> Message:
    return Message(id=id, sender="root", to="ceo", type="task", body="b", service="brief")


def case(first: str, *rest: str, owner: str = "ceo", service: str = "brief") -> Case:
    return Case(
        id=first, service=service, owner=owner, tasks=[task(first), *map(task, rest)], result=None, state="open", playbook=0, used=0,
        reworks=len(rest), budget=1, runs=0, lessons=[], verdicts=[], started=None, finished=None,
    )


def test_it_is_a_case_history() -> None:
    assert isinstance(FixedCaseHistory(), CaseHistory)


def test_it_answers_with_the_cases_of_the_owner_and_service_asked_for() -> None:
    one, two, other = case("T1"), case("T2"), case("T3", owner="ops")
    history = FixedCaseHistory([one, two, other, case("T4", service="x")])
    assert history.cases("ceo", "brief") == [one, two] and history.cases("ops", "brief") == [other] and history.cases("ghost", "brief") == []


def test_every_task_of_a_chain_finds_its_case() -> None:
    chain = case("T1", "T2")
    history = FixedCaseHistory([case("T0"), chain])
    assert history.case_of(task("T1")) is chain and history.case_of(task("T2")) is chain and history.case_of(task("T9")) is None


def test_the_timeline_is_the_one_put_in() -> None:
    history = FixedCaseHistory(timelines={("ceo", "brief"): [(1, T)]})
    assert history.playbook_timeline("ceo", "brief") == [(1, T)] and history.playbook_timeline("ceo", "other") == []


def test_an_empty_history_has_nothing() -> None:
    history = FixedCaseHistory()
    assert history.cases("ceo", "brief") == [] and history.case_of(task("T1")) is None
