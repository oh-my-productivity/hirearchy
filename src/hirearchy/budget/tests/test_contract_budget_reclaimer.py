"""Contract of ``BudgetReclaimer``: the note that moves unspent runs back to the manager, over the derived budgets (on disk and in memory) and over the
fake that holds numbers.

What the callers rely on: only an idle direct report can be reclaimed from, the refusals say why in the words agents are shown, and the transfer is one
note, written on the report's behalf, that nobody is woken by."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.budget import BudgetReclaimer
from hirearchy.budget.testing import IMPLEMENTATIONS, BudgetWorld
from hirearchy.kernel import Message, OrgError, parent

from ._support import assign, grant, make

ENG, QA, OPS = "ceo/eng", "ceo/qa", "ceo/ops"


@pytest.fixture(params=IMPLEMENTATIONS[BudgetReclaimer], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> BudgetWorld:
    made = make(request, tmp_path)
    assert isinstance(made.reclaimer, BudgetReclaimer)
    return made


def idle(w: BudgetWorld, addr: str, runs: int) -> None:
    """``addr`` was granted ``runs`` by its manager and has read the grant: it has nothing to do and holds the runs."""
    grant(w, parent(addr) or "root", addr, runs)
    w.begin_run(addr)
    w.end_run(addr)


def refusal(w: BudgetWorld, actor: str, report: str, budget: int | None = None) -> str:
    with pytest.raises(OrgError) as e:
        w.reclaimer.reclaim(actor, report, budget)
    return str(e.value)


# ------------------------------------------------------------------------------ the transfer


def test_everything_is_reclaimed_by_default(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    msg = w.reclaimer.reclaim("ceo", "eng")
    assert msg.budget == 3 and w.query.budget(ENG) == 0


def test_the_note_is_from_the_report_to_the_manager_and_wakes_nobody(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    msg = w.reclaimer.reclaim("ceo", "eng")
    assert (msg.sender, msg.to, msg.type, msg.wake, msg.hops, msg.reply_to, msg.status) == (ENG, "ceo", "note", False, 0, None, None)
    assert msg.id and msg.created


def test_the_note_says_what_happened(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    msg = w.reclaimer.reclaim("ceo", "eng", 2)
    assert msg.title == "budget reclaimed by ceo"
    assert msg.body == (
        "ceo reclaimed 2 unspent run(s) from ceo/eng (1 left with it). "
        "The runtime wrote this note on ceo/eng's behalf; ceo/eng received nothing and was not woken."
    )


def test_the_note_is_in_the_report_s_sent_box_and_the_manager_s_inbox_only(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    msg = w.reclaimer.reclaim("ceo", "eng")
    assert msg.id in [m.id for m in w.sent(ENG)] and msg.id in [m.id for m in w.inbox("ceo")]
    assert msg.id not in [m.id for m in w.inbox(ENG)]  # the report received nothing
    assert not w.mail.unread("ceo") and not w.mail.unread(ENG)  # nobody is woken


def test_the_manager_gets_what_the_report_lost(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 12)
    idle(w, ENG, 3)
    manager = w.query.budget("ceo")
    assert manager is not None
    w.reclaimer.reclaim("ceo", "eng")
    assert (w.query.budget("ceo"), w.query.budget(ENG)) == (manager + 3, 0)


def test_a_partial_amount_leaves_the_rest_with_the_report(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    msg = w.reclaimer.reclaim("ceo", "eng", 2)
    assert msg.budget == 2 and w.query.budget(ENG) == 1
    assert w.reclaimer.reclaim("ceo", "eng", 1).budget == 1 and w.query.budget(ENG) == 0


def test_the_report_may_be_named_by_its_full_address(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    assert w.reclaimer.reclaim("ceo", ENG, 2).sender == ENG


def test_a_second_reclaim_finds_nothing(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    w.reclaimer.reclaim("ceo", "eng")
    assert refusal(w, "ceo", "eng") == "ceo/eng has no unspent budget to reclaim (0 run(s) left)"


def test_root_reclaims_from_its_direct_report_and_the_runs_leave_the_org(w: BudgetWorld) -> None:
    idle(w, "ceo", 5)
    msg = w.reclaimer.reclaim("root", "ceo", 2)
    assert (msg.sender, msg.to, msg.budget) == ("ceo", "root", 2)
    assert w.query.budget("ceo") == 3 and w.query.budget("root") is None
    assert not w.mail.unread("root")


def test_an_agent_that_does_not_exist_cannot_reclaim(w: BudgetWorld) -> None:
    assert refusal(w, "ghost", "eng") == "no such agent: ghost"


# ------------------------------------------------------------------------------ whom


def test_only_direct_reports_can_be_reclaimed_from(w: BudgetWorld) -> None:
    idle(w, "ceo/ops/dev", 2)
    idle(w, ENG, 2)
    for actor, target in (
        ("root", "ceo/ops/dev"),  # a grandchild of root
        ("ceo", "ceo/ops/dev"),  # a grandchild
        ("ceo/ops/dev", "ceo/ops"),  # a report reclaiming from its manager
        (OPS, ENG),  # a cousin
        ("ceo", "ceo"),  # itself
        ("ceo", "root"),
        ("ceo", "nobody"),
    ):
        assert "you can only reclaim budget from your direct reports (yours: " in refusal(w, actor, target)
    assert w.query.budget("ceo/ops/dev") == 2 and w.query.budget(ENG) == 2


def test_the_refusal_lists_the_direct_reports(w: BudgetWorld) -> None:
    assert refusal(w, "ceo", "ceo/ops/dev") == (
        "you can only reclaim budget from your direct reports (yours: ceo/eng, ceo/ops, ceo/qa); 'ceo/ops/dev' is not one. "
        "Ask a manager to reclaim from its own team."
    )


def test_an_agent_without_reports_is_told_there_are_none(w: BudgetWorld) -> None:
    assert refusal(w, ENG, "ceo") == (
        "you can only reclaim budget from your direct reports (yours: none); 'ceo' is not one. Ask a manager to reclaim from its own team."
    )


# ------------------------------------------------------------------------------ how much


def test_less_than_one_run_is_refused(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    for bad in (0, -2):
        assert refusal(w, "ceo", "eng", bad) == "budget must be at least 1 run (omit it to reclaim everything the report has left)"
    assert w.query.budget(ENG) == 3


def test_more_than_is_left_is_refused(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    assert refusal(w, "ceo", "eng", 4) == "ceo/eng has only 3 unspent run(s); you asked for 4"


def test_a_report_with_nothing_left_is_refused(w: BudgetWorld) -> None:
    assert refusal(w, "ceo", "eng") == "ceo/eng has no unspent budget to reclaim (0 run(s) left)"
    w.use_run(ENG)
    assert refusal(w, "ceo", "eng") == "ceo/eng has no unspent budget to reclaim (-1 run(s) left)"


# ------------------------------------------------------------------------------ only an idle report


def busy(why: str, who: str = ENG) -> str:
    return f"{who} is busy ({why}), so its runs are not stranded. Wait until it has reported, or leave its budget with it."


def test_a_report_that_is_running_is_busy(w: BudgetWorld) -> None:
    grant(w, "ceo", ENG, 3)
    w.begin_run(ENG)
    assert refusal(w, "ceo", "eng") == busy("it is running now")


def test_a_report_with_an_open_task_is_busy(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    assign(w, "ceo", ENG)
    w.begin_run(ENG)
    w.end_run(ENG)
    assert refusal(w, "ceo", "eng") == busy("it has 1 open task(s)")


def test_a_report_with_an_outstanding_delegation_is_busy(w: BudgetWorld) -> None:
    idle(w, OPS, 6)
    assign(w, OPS, "ceo/ops/dev", 2)
    assert refusal(w, "ceo", "ops") == busy("it has 1 delegation(s) still outstanding", OPS)


def test_a_report_with_waking_mail_is_busy(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    w.post(Message(sender="ceo", to=ENG, type="note", body="a question", title="q"))
    assert refusal(w, "ceo", "eng") == busy("it has 1 unread message(s) that will wake it")


def test_every_reason_is_given_in_the_same_order(w: BudgetWorld) -> None:
    grant(w, "ceo", ENG, 3)
    assign(w, "ceo", ENG)
    w.begin_run(ENG)
    assign(w, ENG, "ceo/ops/dev")
    w.post(Message(sender="ceo", to=ENG, type="note", body="a question", title="q"))
    assert refusal(w, "ceo", "eng") == busy(
        "it is running now; it has 1 open task(s); it has 1 delegation(s) still outstanding; it has 1 unread message(s) that will wake it"
    )


def test_mail_that_does_not_wake_is_no_reason_to_refuse(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    w.post(Message(sender="runtime", to=ENG, type="note", body="fyi", title="n", wake=False))
    assert w.reclaimer.reclaim("ceo", "eng").budget == 3


def test_a_refusal_moves_nothing(w: BudgetWorld) -> None:
    idle(w, ENG, 3)
    assign(w, "ceo", ENG)
    refusal(w, "ceo", "eng")
    assert [m for m in w.sent(ENG) if m.title.startswith("budget reclaimed")] == []
    assert w.query.budget(ENG) == 3
