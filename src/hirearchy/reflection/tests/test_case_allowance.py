"""``CaseAllowanceOf``: what is left of the runs the user approved for a case, derived from the cases of a service and its contract (D-E5-1, design 4.5).

The services suite of ``CaseAllowance`` runs against it too (the pattern of ``test_case_judged_versions``), over a world where ``ceo`` offers
``weekly-brief`` and no task is in a case; the behaviour tests follow."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection._allowance import CaseAllowanceOf
from hirearchy.reflection.testing import ReflectionWorld, fs_world, memory_world
from hirearchy.services import CaseAllowance

# The suite that every ``CaseAllowance`` passes: the same functions, run against this package's implementation.
from hirearchy.services.tests.test_contract_case_allowance import (  # noqa: F401  (imported to be collected here)
    test_a_task_that_is_in_no_case_has_no_allowance,
    test_the_answer_is_none_or_a_whole_number_of_runs,
    test_the_answer_is_the_same_every_time,
)

from ._support import SERVICE, ask, define, deliver, populated, rework


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@pytest.fixture
def allowance(w: ReflectionWorld) -> CaseAllowance:
    define(w)
    return CaseAllowanceOf(w.history, w.s.catalog)


def test_it_is_a_case_allowance(allowance: CaseAllowance) -> None:
    assert isinstance(allowance, CaseAllowance)


def test_what_is_left_is_the_approved_runs_less_what_the_users_requests_used_or_the_team_holds(w: ReflectionWorld, allowance: CaseAllowance) -> None:
    first = ask(w)
    deliver(w, first, runs=3, budget=7)  # 10 handed down, 3 used, 7 came back: 3 committed
    assert allowance.left("ceo", SERVICE, first.id) == 7
    again = rework(w, first, budget=4)  # the rework's 4 are committed too, and raise the approval by what was not left (nothing)
    assert allowance.left("ceo", SERVICE, first.id) == allowance.left("ceo", SERVICE, again.id) == 10 - (3 + 4)


def test_what_is_left_can_be_zero_or_below(w: ReflectionWorld, allowance: CaseAllowance) -> None:
    first = ask(w)
    deliver(w, first, runs=10)  # all 10 used, none back
    assert allowance.left("ceo", SERVICE, first.id) == 0
    second = ask(w, "again")
    deliver(w, second, runs=12)  # the team ran past what was handed down
    assert allowance.left("ceo", SERVICE, second.id) == -2


def test_an_explicit_top_up_raises_the_approval_by_its_excess(w: ReflectionWorld, allowance: CaseAllowance) -> None:
    first = ask(w, budget=15)  # approved 15 beyond the contract's 10
    deliver(w, first, runs=5, budget=10)
    assert allowance.left("ceo", SERVICE, first.id) == 15 - 5


def test_a_retired_service_has_no_allowance(w: ReflectionWorld, allowance: CaseAllowance) -> None:
    first = ask(w)
    deliver(w, first)
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    assert allowance.left("ceo", SERVICE, first.id) is None


def test_an_agent_client_has_no_allowance(w: ReflectionWorld, allowance: CaseAllowance) -> None:
    w.s.d.post(Message(sender="root", to="ceo", type="note", body="runs for you", title="grant", budget=60))
    define(w, "ceo/eng", "inner", actor="ceo")
    first = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    deliver(w, first)
    assert allowance.left("ceo/eng", "inner", first.id) is None
