"""Contract of ``Retirement``: removing a direct report and its team, over the real classes on disk and over the in-memory fakes.

What the callers rely on (the MCP tool, the CLI, the blueprint): who can be retired by whom, the failed results the team's open tasks leave behind,
the runs that go back to the parent as a note that wakes nobody, the archive, and the one event."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.hierarchy import Retired, Retirement
from hirearchy.hierarchy.testing import IMPLEMENTATIONS, HierarchyWorld
from hirearchy.kernel import RUNTIME, Message, OrgError

from ._support import BOSS, WORKER, assign, grant, make

ENG = "ceo/eng"
MGR, W = "ceo/mgr", "ceo/mgr/w"
STAMP = "20261018T100000"  # the clock of the worlds, as the archive names it


@pytest.fixture(params=IMPLEMENTATIONS[Retirement], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> HierarchyWorld:
    made = make(request, tmp_path)
    assert isinstance(made.retirement, Retirement)
    return made


def team(w: HierarchyWorld) -> HierarchyWorld:
    """root -> ceo(20) -> mgr(10, used 2) -> w(4, used 1); ceo also keeps eng."""
    w.agent(MGR, BOSS)
    w.agent(W, WORKER)
    grant(w, "root", "ceo", 20)
    grant(w, "ceo", MGR, 10)
    grant(w, MGR, W, 4)
    w.use_run(MGR)
    w.use_run(MGR)
    w.use_run(W)
    assert (w.budget.budget("ceo"), w.budget.budget(MGR), w.budget.budget(W)) == (10, 4, 3)
    return w


def refusal(w: HierarchyWorld, actor: str, name: str) -> str:
    with pytest.raises(OrgError) as e:
        w.retirement.retire_team(actor, name, "no")
    return str(e.value)


def runtime_notes(w: HierarchyWorld) -> list[Message]:
    return [m for m in w.delivered if m.sender == RUNTIME]


# ------------------------------------------------------------------------------ who can retire whom


def test_retire_returns_the_address(w: HierarchyWorld) -> None:
    assert w.retirement.retire("ceo", "eng", "done") == ENG


def test_retire_team_returns_what_was_retired_and_what_went_back(w: HierarchyWorld) -> None:
    team(w)
    assert w.retirement.retire_team("ceo", "mgr", "restructuring") == Retired(MGR, 7, "ceo")


def test_a_short_name_and_a_full_address_both_name_a_direct_report(w: HierarchyWorld) -> None:
    w.agent("ceo/ops", WORKER)
    assert w.retirement.retire("ceo", "ops", "short") == "ceo/ops"
    assert w.retirement.retire("ceo", ENG, "full") == ENG
    w.agent(ENG, WORKER)
    assert w.retirement.retire("root", ENG, "root, full address") == ENG


def test_the_actor_is_normalized(w: HierarchyWorld) -> None:
    assert w.retirement.retire("ceo/", "eng", "done") == ENG


def test_root_may_retire_any_agent_by_its_full_address(w: HierarchyWorld) -> None:
    team(w)
    assert w.retirement.retire("root", W, "deep") == W
    assert w.agents.agents() == ["ceo", ENG, MGR]


def test_nobody_else_can_be_retired(w: HierarchyWorld) -> None:
    team(w)
    direct = "you can only retire your direct reports"
    assert refusal(w, "ceo", W) == direct
    assert refusal(w, ENG, "ceo") == "no such agent: ceo/eng/ceo"  # a short name is a report of the actor
    assert refusal(w, MGR, "root") == "no such agent: ceo/mgr/root"
    assert refusal(w, MGR, ENG) == direct
    assert refusal(w, "ceo", "mgr/w") == "no such agent: mgr/w"
    assert refusal(w, "ceo", "ceo") == "no such agent: ceo/ceo"
    assert refusal(w, "ceo", "root") == "no such agent: ceo/root"
    assert refusal(w, "ceo", "ghost") == "no such agent: ceo/ghost"
    assert w.agents.agents() == ["ceo", ENG, MGR, W]
    assert w.events.events == [] and runtime_notes(w) == []


def test_root_of_the_organization_cannot_be_retired(w: HierarchyWorld) -> None:
    assert refusal(w, "root", "root") == "the root of the organization cannot be retired"
    assert refusal(w, "root", "") == "the root of the organization cannot be retired"


def test_an_actor_that_does_not_exist_is_refused(w: HierarchyWorld) -> None:
    assert refusal(w, "ghost", "eng") == "no such agent: ghost"


# ------------------------------------------------------------------------------ the archive


def test_the_whole_team_moves_to_the_archive(w: HierarchyWorld) -> None:
    team(w)
    w.retirement.retire_team("ceo", "mgr", "restructuring")
    assert not w.agents.exists(MGR) and not w.agents.exists(W)
    assert w.listing(".retired") == [f"ceo.mgr-{STAMP}"]
    assert w.read(f".retired/ceo.mgr-{STAMP}/AGENT.md") is not None and w.read(f".retired/ceo.mgr-{STAMP}/w/AGENT.md") is not None
    assert w.agents.children("ceo") == [ENG]


def test_the_archive_is_named_after_the_clock(w: HierarchyWorld) -> None:
    w.clock.advance(3725)
    w.retirement.retire("ceo", "eng", "later")
    assert w.listing(".retired") == ["ceo.eng-20261018T110205"]


# ------------------------------------------------------------------------------ the tasks the team owes


def test_an_open_task_the_team_owes_is_failed_upward(w: HierarchyWorld) -> None:
    sub = assign(w, "ceo", ENG, title="Sub")
    w.retirement.retire("ceo", "eng", "no longer needed")
    (result,) = [m for m in w.delivered if m.type == "result"]
    assert (result.sender, result.to, result.title, result.reply_to, result.status) == (ENG, "ceo", "Sub", sub.id, "failed")
    assert result.body == "## Summary\nAgent ceo/eng was retired by ceo: no longer needed"
    assert result.budget == 0 and result.wake is True
    assert w.tasks.outstanding("ceo") == []


def test_every_agent_of_the_team_fails_what_it_owes(w: HierarchyWorld) -> None:
    team(w)
    first = assign(w, "ceo", MGR, title="Plan")
    second = assign(w, "root", W, title="Build")
    w.retirement.retire("ceo", "mgr", "x")
    failed = {(m.sender, m.to, m.reply_to): m.body for m in w.delivered if m.type == "result"}
    assert failed == {
        (MGR, "ceo", first.id): "## Summary\nAgent ceo/mgr was retired by ceo: x",
        (W, "root", second.id): "## Summary\nAgent ceo/mgr/w was retired by ceo: x",
    }


def test_a_task_inside_the_team_is_not_failed(w: HierarchyWorld) -> None:
    team(w)
    assign(w, MGR, W, title="Inner")
    w.retirement.retire("ceo", "mgr", "x")
    assert [m for m in w.delivered if m.type == "result"] == []


def test_a_task_from_an_agent_that_is_gone_is_not_answered(w: HierarchyWorld) -> None:
    team(w)
    assign(w, ENG, MGR, title="From a ghost to be")
    w.retirement.retire("ceo", "eng", "first")
    w.retirement.retire("ceo", "mgr", "second")
    assert [m for m in w.delivered if m.type == "result"] == []


def test_a_task_that_is_answered_already_is_left_alone(w: HierarchyWorld) -> None:
    sub = assign(w, "ceo", ENG, title="Sub")
    w.post(Message(sender=ENG, to="ceo", type="result", body="done", title="Sub", reply_to=sub.id, status="done"))
    before = len(w.delivered)
    w.retirement.retire("ceo", "eng", "x")
    assert [m for m in w.delivered[before:] if m.type == "result"] == []


# ------------------------------------------------------------------------------ the runs that go back


def test_the_unspent_runs_of_the_whole_team_go_back_to_the_parent(w: HierarchyWorld) -> None:
    team(w)
    result = w.retirement.retire_team("ceo", "mgr", "restructuring")
    assert (result.addr, result.refunded, result.refunded_to) == (MGR, 7, "ceo")
    assert w.budget.budget("ceo") == 17  # 20 granted - 3 runs the retired team used


def test_the_refund_is_one_note_from_the_runtime_that_wakes_nobody(w: HierarchyWorld) -> None:
    team(w)
    before, unread = len(w.delivered), w.mail.unread("ceo")  # the grant of root is still unread
    w.retirement.retire_team("ceo", "mgr", "restructuring")
    (note,) = w.delivered[before:]
    assert (note.sender, note.to, note.type, note.budget, note.wake) == (RUNTIME, "ceo", "note", 7, False)
    assert note.title == "Budget returned from ceo/mgr"
    assert note.body == (
        "`ceo/mgr` and its team were retired by ceo (restructuring). Their unspent budget, 7 run(s), is returned to you with this note."
    )
    assert note.id in [m.id for m in w.inbox("ceo")] and w.mail.unread("ceo") == unread and not w.mail.has_inflight("ceo")


def test_the_actor_named_in_the_note_is_the_one_who_retired(w: HierarchyWorld) -> None:
    team(w)
    before = len(w.delivered)
    w.retirement.retire_team("root", W, "deep")  # w's parent is mgr, not root: a refund is due
    (note,) = w.delivered[before:]
    assert note.to == MGR and "were retired by root (deep)" in note.body


def test_a_team_that_overspent_returns_nothing(w: HierarchyWorld) -> None:
    grant(w, "root", "ceo", 10)
    grant(w, "ceo", ENG, 2)
    for _ in range(5):
        w.use_run(ENG)
    assert w.budget.budget(ENG) == -3
    assert w.retirement.retire_team("ceo", "eng", "x") == Retired(ENG, 0, None)
    assert w.budget.budget("ceo") == 8 and runtime_notes(w) == []


def test_an_overspending_member_is_set_off_against_the_others(w: HierarchyWorld) -> None:
    team(w)
    w.use_run(W)
    w.use_run(W)
    w.use_run(W)
    w.use_run(W)  # w: 3 - 4 = -1; mgr still 4
    assert w.retirement.retire_team("ceo", "mgr", "x").refunded == 3


def test_nothing_is_returned_when_the_parent_is_root(w: HierarchyWorld) -> None:
    grant(w, "root", "ceo", 3)
    before = len(w.delivered)
    assert w.retirement.retire_team("root", "ceo", "x") == Retired("ceo", 0, None)  # root has no limit: nothing to credit
    assert w.delivered[before:] == []


def test_a_team_without_runs_returns_nothing(w: HierarchyWorld) -> None:
    before = len(w.delivered)
    assert w.retirement.retire_team("ceo", "eng", "x") == Retired(ENG, 0, None)
    assert w.delivered[before:] == []


# ------------------------------------------------------------------------------ the event


def test_one_event_says_who_retired_whom(w: HierarchyWorld) -> None:
    team(w)
    w.retirement.retire_team("ceo", "mgr", "restructuring")
    (event,) = w.events.events
    assert (event.kind, event.actor) == ("agent.retire", "ceo")
    assert event.fields == {
        "agent": MGR, "by": "ceo", "reason": "restructuring", "returned_budget": 7, "team": [MGR, W],
    }


def test_the_event_has_no_budget_when_nothing_went_back(w: HierarchyWorld) -> None:
    w.retirement.retire("root", "ceo", "x")
    assert w.events.events[0].fields["returned_budget"] == 0 and w.events.events[0].fields["team"] == ["ceo", ENG]


def test_a_long_reason_is_clipped_in_the_event_not_in_the_note(w: HierarchyWorld) -> None:
    team(w)
    reason = "because " * 100
    w.retirement.retire_team("ceo", "mgr", reason)
    shown = w.events.events[0].fields["reason"]
    assert isinstance(shown, str) and len(shown) == 500 and shown.endswith("…") and reason.startswith(shown[:-1])
    assert reason in runtime_notes(w)[0].body


def test_a_refused_retire_leaves_no_event(w: HierarchyWorld) -> None:
    refusal(w, "ceo", "ceo")
    assert w.events.events == []
