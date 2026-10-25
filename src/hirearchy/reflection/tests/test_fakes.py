"""``FixedCaseHistory``: the cases a test puts in."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection import BarChanges, CharterMark, Case, CaseHistory, ModelMark
from hirearchy.reflection._ports import BarHistory
from hirearchy.reflection.testing import FixedBarHistory, FixedCaseHistory, NoBarHistory

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


def test_its_chains_are_its_cases_kept_since_a_time_whatever_the_runs() -> None:
    early, late = case("T1"), case("T2")
    early.started, late.started = T, T + timedelta(days=1)
    unstarted = case("T3")
    history = FixedCaseHistory([early, late, unstarted, case("T4", owner="ops")])
    assert history.chains("ceo", "brief", since=None, runs=False) == [early, late, unstarted]
    assert history.chains("ceo", "brief", since=T + timedelta(days=1), runs=True) == [late, unstarted]  # a case without a start is kept
    assert history.chains("ghost", "brief", since=None, runs=True) == []


def test_its_one_off_cases_are_the_cases_it_holds_without_a_service() -> None:
    plain, service_case = case("T1", service=""), case("T2")
    history = FixedCaseHistory([plain, service_case])
    assert history.one_off_cases() == history.one_off_cases(runs=False) == [plain]
    assert history.cases("ceo", "") == [plain]


def test_an_empty_history_has_nothing() -> None:
    history = FixedCaseHistory()
    assert history.cases("ceo", "brief") == [] and history.case_of(task("T1")) is None and history.one_off_cases() == []


def test_no_bar_history_is_unknown_and_fixed_bar_history_returns_its_marks() -> None:
    assert isinstance(NoBarHistory(), BarHistory) and isinstance(FixedBarHistory(), BarHistory)
    assert NoBarHistory().changes(["lead"]) == BarChanges(known=False)
    marks = (CharterMark("lead", "a" * 40, T), ModelMark("ORG.md", "effort", "high", "xhigh", "b" * 40, T))
    assert FixedBarHistory(marks).changes(["lead"]) == BarChanges(known=True, marks=marks)
    assert FixedBarHistory(marks, truncated=True, skipped=2).changes([]) == BarChanges(known=True, marks=marks, truncated=True, skipped=2)
    assert FixedBarHistory().changes(["lead"]) == BarChanges(known=True)
