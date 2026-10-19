"""Which agents may start a run: waking mail, no pause, budget left; no budget pauses the agent and tells its parent."""

from __future__ import annotations

from orgmcp.scheduler._admission import BudgetGate
from orgmcp.scheduler.testing import LifecycleWorld, lifecycle_world



def gate(w: LifecycleWorld) -> BudgetGate:
    return BudgetGate(w.box, w.pauses, w.budgets, w.delivery, w.notices, w.console)


def test_an_agent_without_waking_mail_is_not_admitted() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    assert gate(w).admit("ceo") is False
    w.mail_to("ceo", wake=False)
    assert gate(w).admit("ceo") is False


def test_an_agent_with_mail_and_budget_is_admitted() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    w.mail_to("ceo")
    assert gate(w).admit("ceo") is True
    assert w.console.lines == []


def test_a_paused_agent_is_not_admitted() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    w.mail_to("ceo")
    w.pauses.pause("ceo", "paused by the human", by="root")
    assert gate(w).admit("ceo") is False


def test_a_budget_pause_is_lifted_when_budget_is_back() -> None:
    w = lifecycle_world()
    w.hire("ceo", budget=2)
    w.mail_to("ceo")
    w.pauses.pause("ceo", "budget", by="runtime")
    assert gate(w).admit("ceo") is True
    assert w.pauses.paused("ceo") is None


def test_an_agent_out_of_budget_is_paused_and_its_parent_told_with_the_trace_of_what_waits() -> None:
    w = lifecycle_world()
    w.hire("ceo/eng", budget=0)
    w.mail_to("ceo/eng", trace="t9")
    assert gate(w).admit("ceo/eng") is False
    assert w.pauses.paused("ceo/eng") == "budget"
    (note,) = w.delivery.messages
    assert (note.to, note.title, note.trace, note.body) == ("ceo", "ceo/eng is out of budget", "t9", "budget: ceo/eng | 1")
    assert w.console.lines == ["ceo/eng: out of budget, paused, parent notified"]


def test_the_parent_of_a_top_level_agent_is_root() -> None:
    w = lifecycle_world()
    w.hire("ceo", budget=0)
    w.mail_to("ceo")
    gate(w).admit("ceo")
    assert [m.to for m in w.delivery.messages] == ["root"]


def test_events_of_the_pause_are_the_pause_stores_not_the_gates() -> None:
    w = lifecycle_world()
    w.hire("ceo", budget=0)
    w.mail_to("ceo")
    gate(w).admit("ceo")
    assert [e.kind for e in w.events.events] == ["agent.pause"]
