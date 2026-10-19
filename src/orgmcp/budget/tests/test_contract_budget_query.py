"""Contract of ``BudgetQuery``: the derived budgets (over the mailboxes and run logs on disk and in memory) and the fake that holds numbers behave alike.

What the callers rely on: budget is what was received minus what was handed down minus the runs made; root has no limit; ``delegable`` keeps a
run per outstanding delegation and one for the next; ``grant_hint`` says in words what the recipient of a grant can do now."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.budget import BudgetQuery
from orgmcp.budget.testing import IMPLEMENTATIONS, BudgetWorld
from orgmcp.kernel import Message

from ._support import assign, grant, make, report


pytestmark = pytest.mark.xfail(strict=True, reason="red: B-budget")


@pytest.fixture(params=IMPLEMENTATIONS[BudgetQuery], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> BudgetWorld:
    made = make(request, tmp_path)
    assert isinstance(made.query, BudgetQuery)
    return made


# ------------------------------------------------------------------------------ budget = received - given - runs


def test_an_agent_that_received_nothing_has_nothing(w: BudgetWorld) -> None:
    assert w.query.budget("ceo") == 0 and w.query.budget("ceo/eng") == 0


def test_root_has_no_limit(w: BudgetWorld) -> None:
    assert w.query.budget("root") is None
    grant(w, "ceo", "root", 0)
    assert w.query.budget(" /root/ ") is None


def test_what_was_received_counts(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    grant(w, "root", "ceo", 2)
    assert w.query.budget("ceo") == 7


def test_what_was_handed_down_is_subtracted_and_credited_to_the_recipient(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    grant(w, "ceo", "ceo/eng", 2)
    assert (w.query.budget("ceo"), w.query.budget("ceo/eng")) == (3, 2)


def test_a_run_consumes_one_run(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    w.use_run("ceo")
    w.use_run("ceo")
    assert w.query.budget("ceo") == 3 and w.query.budget("ceo/eng") == 0


def test_runs_made_beyond_the_budget_make_it_negative(w: BudgetWorld) -> None:
    w.use_run("ceo/eng")
    assert w.query.budget("ceo/eng") == -1


def test_a_task_carries_its_budget_like_a_note(w: BudgetWorld) -> None:
    assign(w, "root", "ceo", 6)
    assign(w, "ceo", "ceo/eng", 2)
    assert (w.query.budget("ceo"), w.query.budget("ceo/eng")) == (4, 2)


def test_a_result_returns_its_budget_to_the_assigner(w: BudgetWorld) -> None:
    task = assign(w, "root", "ceo", 5)
    w.use_run("ceo")
    report(w, task, runs=4)
    assert w.query.budget("ceo") == 0 and w.query.budget("root") is None


def test_it_does_not_matter_where_in_its_boxes_a_message_is(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    assert w.query.budget("ceo") == 5  # in the inbox
    w.begin_run("ceo")
    assert w.query.budget("ceo") == 5  # in flight
    w.end_run("ceo")
    assert w.query.budget("ceo") == 5  # read


def test_the_address_may_be_spelled_loosely(w: BudgetWorld) -> None:
    grant(w, "root", "ceo/eng", 3)
    assert w.query.budget(" /ceo/eng/ ") == 3


def test_the_runtime_has_no_account(w: BudgetWorld) -> None:
    w.post(Message(sender="runtime", to="ceo", type="note", body="b", title="t"))
    assert w.query.budget("ceo") == 0


# ------------------------------------------------------------------------------ delegable


def test_delegable_keeps_one_run_for_the_result_of_the_next_delegation(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 3)
    assert w.query.delegable("ceo") == (3, 0, 2)


def test_delegable_keeps_one_more_per_outstanding_delegation(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 3)
    assign(w, "ceo", "ceo/eng", 1)
    assert w.query.delegable("ceo") == (2, 1, 0)
    grant(w, "root", "ceo", 1)
    assert w.query.delegable("ceo") == (3, 1, 1)


def test_delegable_is_never_below_zero(w: BudgetWorld) -> None:
    grant(w, "root", "ceo/eng", 1)
    assert w.query.delegable("ceo/eng") == (1, 0, 0)
    assert w.query.delegable("ceo/qa") == (0, 0, 0)


def test_an_answered_delegation_is_no_longer_outstanding(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 5)
    task = assign(w, "ceo", "ceo/eng", 2)
    report(w, task)
    assert w.query.delegable("ceo") == (3, 0, 2)


def test_delegable_counts_root_as_having_nothing(w: BudgetWorld) -> None:
    assign(w, "root", "ceo", 1)
    assert w.query.delegable("root") == (0, 1, 0)


# ------------------------------------------------------------------------------ grant_hint


def test_the_hint_for_a_recipient_that_can_hand_something_down(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 3)
    assert w.query.grant_hint("ceo") == (
        "`ceo` now has 3 run(s) and 0 outstanding delegation(s); with one more delegation it can hand down at most 2 run(s)."
    )


def test_the_hint_for_a_recipient_that_cannot_delegate_says_how_much_more_it_needs(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 3)
    assign(w, "ceo", "ceo/eng", 1)
    assert w.query.grant_hint("ceo") == (
        "`ceo` now has 2 run(s) and 1 outstanding delegation(s): with 2 run(s) and 1 outstanding delegation(s) it cannot delegate anything; it can "
        "only process results or work itself - grant at least 1 more (a budget of 3) to allow one delegation of 1 run."
    )


def test_the_hint_for_a_recipient_with_no_runs_at_all(w: BudgetWorld) -> None:
    assert w.query.grant_hint("ceo/ops") == (
        "`ceo/ops` now has 0 run(s) and 0 outstanding delegation(s): with 0 run(s) and 0 outstanding delegation(s) it cannot delegate anything; it can "
        "only process results or work itself - grant at least 2 more (a budget of 2) to allow one delegation of 1 run."
    )


def test_a_recipient_that_is_over_the_need_is_asked_for_nothing_more(w: BudgetWorld) -> None:
    grant(w, "root", "ceo/ops", 2)
    assert w.query.grant_hint("ceo/ops").endswith("it can hand down at most 1 run(s).")


def test_there_is_no_hint_for_an_agent_that_cannot_hire(w: BudgetWorld) -> None:
    grant(w, "ceo", "ceo/eng", 3)
    assert w.query.grant_hint("ceo/eng") == ""


def test_there_is_no_hint_for_an_agent_that_does_not_exist(w: BudgetWorld) -> None:
    assert w.query.grant_hint("ghost") == ""
