"""Contract of ``AllocationPolicy`` over the derived budgets (on disk and in memory) and over the fake that holds numbers.

What the callers rely on: one run per outstanding delegation stays in reserve (and one for the next delegation's result), the texts that refuse
are the ones agents are shown, a delegation without a budget gets what can be afforded, and a final result carries back everything that is left
only when nothing else needs it."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.budget import AllocationPolicy
from hirearchy.budget.testing import IMPLEMENTATIONS, BudgetWorld
from hirearchy.kernel import Message, OrgError

from ._support import assign, grant, make, report


@pytest.fixture(params=IMPLEMENTATIONS[AllocationPolicy], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> BudgetWorld:
    made = make(request, tmp_path)
    assert isinstance(made.policy, AllocationPolicy)
    return made


# ------------------------------------------------------------------------------ check_allocation


def test_root_may_hand_down_anything(w: BudgetWorld) -> None:
    w.policy.check_allocation("root", 1_000_000, True)


def test_nothing_to_hand_down_always_passes(w: BudgetWorld) -> None:
    w.policy.check_allocation("ceo/eng", 0, True)


def test_an_agent_may_hand_down_what_it_has_beyond_the_reserve(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    w.policy.check_allocation("ceo", 5, False)
    w.policy.check_allocation("ceo", 4, True)  # one run is kept for the result of the new delegation


def test_a_new_delegation_keeps_one_run_for_its_result(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    with pytest.raises(OrgError) as e:
        w.policy.check_allocation("ceo", 5, True)
    assert str(e.value) == (
        "not enough budget: you have 5 run(s) and must keep 1 in reserve (one per outstanding delegation, to process its result), "
        "so you can hand down at most 4. Ask your parent for more budget or do less."
    )


def test_an_outstanding_delegation_keeps_a_run_in_reserve(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 6)
    assign(w, "ceo", "ceo/eng", 2)
    w.policy.check_allocation("ceo", 3, False)
    with pytest.raises(OrgError) as e:
        w.policy.check_allocation("ceo", 4, False)
    assert "you have 4 run(s) and must keep 1 in reserve" in str(e.value) and "at most 3." in str(e.value)


def test_the_most_that_can_be_handed_down_is_never_negative(w: BudgetWorld) -> None:
    with pytest.raises(OrgError) as e:
        w.policy.check_allocation("ceo/eng", 1, True)
    assert "you have 0 run(s) and must keep 1 in reserve" in str(e.value) and "at most 0." in str(e.value)


def test_the_refusal_is_an_org_error(w: BudgetWorld) -> None:
    with pytest.raises(OrgError, match="not enough budget"):
        w.policy.check_allocation("ceo", 1, False)


# ------------------------------------------------------------------------------ default_budget


def test_root_gets_the_default_budget_of_the_settings(w: BudgetWorld) -> None:
    assert w.policy.default_budget("root") == 10
    w.configure("---\nmission: test\ndefault_budget: 4\n---\nrules\n")
    assert w.policy.default_budget("root") == 4


def test_the_default_budget_caps_what_is_given(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 50)
    assert w.policy.default_budget("ceo") == 10


def test_what_can_be_afforded_is_given_when_it_is_less(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 6)
    assert w.policy.default_budget("ceo") == 5  # 6 - (0 outstanding + 1)


def test_an_outstanding_delegation_is_reserved_for(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 8)
    assign(w, "ceo", "ceo/eng", 2)  # 6 left, 1 outstanding
    assert w.policy.default_budget("ceo") == 4  # 6 - (1 + 1)


def test_exactly_the_reserve_left_cannot_afford_a_delegation(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 1)
    with pytest.raises(OrgError) as e:
        w.policy.default_budget("ceo")
    assert str(e.value) == (
        "you cannot afford this delegation: you have 1 run(s) and must keep 1 in reserve "
        "(one per outstanding delegation, plus one to process the result of this one), so nothing is left "
        "to hand down. Options: ask your parent for more budget with `send` and end your run; do the work "
        "yourself; or, if the task cannot be completed without this step, report `blocked` (never `done`) "
        "and say what is missing."
    )


def test_one_run_over_the_reserve_affords_one_run(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 2)
    assert w.policy.default_budget("ceo") == 1


def test_an_agent_without_any_runs_cannot_afford_a_delegation(w: BudgetWorld) -> None:
    with pytest.raises(OrgError, match="you have 0 run"):
        w.policy.default_budget("ceo/ops")


# ------------------------------------------------------------------------------ budget_to_return


def one_run(w: BudgetWorld, runs: int = 5) -> Message:
    """``ceo`` was assigned a task by root with ``runs`` runs and made one run (so it reads its mail)."""
    task = assign(w, "root", "ceo", runs)
    w.begin_run("ceo")
    w.use_run("ceo")
    return task


def test_a_final_result_returns_everything_that_is_left(w: BudgetWorld) -> None:
    task = one_run(w)
    assert w.policy.budget_to_return("ceo", task, "done") == 4
    assert w.policy.budget_to_return("ceo", task, "failed") == 4


def test_a_blocked_result_returns_nothing(w: BudgetWorld) -> None:
    assert w.policy.budget_to_return("ceo", one_run(w), "blocked") == 0


def test_only_the_parent_can_receive_a_return(w: BudgetWorld) -> None:
    grant(w, "root", "ceo/eng", 5)
    task = assign(w, "root", "ceo/eng")  # a task from root to a deep agent: not eng's parent
    w.begin_run("ceo/eng")
    w.use_run("ceo/eng")
    assert w.policy.budget_to_return("ceo/eng", task, "done") == 0


def test_the_parent_of_a_deep_agent_receives_the_return(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 10)
    task = assign(w, "ceo", "ceo/eng", 4)
    w.begin_run("ceo/eng")
    w.use_run("ceo/eng")
    assert w.policy.budget_to_return("ceo/eng", task, "done") == 3


def test_nothing_is_returned_while_another_task_is_open(w: BudgetWorld) -> None:
    first = one_run(w)
    assign(w, "root", "ceo", 4)
    w.begin_run("ceo")  # read: the second task is open, nothing else holds the return back
    assert w.policy.budget_to_return("ceo", first, "done") == 0


def test_the_task_that_is_reported_is_not_another_open_task(w: BudgetWorld) -> None:
    task = one_run(w)
    assert [t.id for t in w.tasks.open_tasks("ceo")] == [task.id]
    assert w.policy.budget_to_return("ceo", task, "done") == 4


def test_nothing_is_returned_while_another_task_is_blocked(w: BudgetWorld) -> None:
    first, second = one_run(w), assign(w, "root", "ceo", 4)
    report(w, first, "blocked")
    w.begin_run("ceo")  # read: the blocked task is the only thing that holds the return back
    assert w.policy.budget_to_return("ceo", second, "done") == 0


def test_a_blocked_task_that_is_reported_again_does_not_hold_itself_back(w: BudgetWorld) -> None:
    task = one_run(w)
    report(w, task, "blocked")
    assert w.policy.budget_to_return("ceo", task, "done") == 4


def test_nothing_is_returned_while_a_delegation_is_outstanding(w: BudgetWorld) -> None:
    task = one_run(w)
    assign(w, "ceo", "ceo/eng", 2)
    assert w.policy.budget_to_return("ceo", task, "done") == 0


def test_nothing_is_returned_while_waking_mail_waits(w: BudgetWorld) -> None:
    task = one_run(w)
    w.post(Message(sender="root", to="ceo", type="note", body="one more thing", title="n"))
    assert w.policy.budget_to_return("ceo", task, "done") == 0


def test_a_note_that_does_not_wake_does_not_hold_the_return_back(w: BudgetWorld) -> None:
    task = one_run(w)
    w.post(Message(sender="runtime", to="ceo", type="note", body="fyi", title="n", wake=False))
    assert w.policy.budget_to_return("ceo", task, "done") == 4


def test_an_answered_delegation_does_not_hold_the_return_back(w: BudgetWorld) -> None:
    task = one_run(w, 8)
    sub = assign(w, "ceo", "ceo/eng", 2)
    report(w, sub)
    w.begin_run("ceo")
    assert w.policy.budget_to_return("ceo", task, "done") == 5  # 8 - 2 - 1 run


def test_an_agent_that_is_over_its_budget_returns_nothing(w: BudgetWorld) -> None:
    task = one_run(w, 1)
    w.use_run("ceo")  # a redelivered run is charged like any run
    assert w.query.budget("ceo") == -1 and w.policy.budget_to_return("ceo", task, "done") == 0
