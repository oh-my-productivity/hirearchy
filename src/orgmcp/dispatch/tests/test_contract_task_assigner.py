"""Contract of ``TaskAssigner``: the assigner over the mailboxes on disk, in memory and over numbers for budgets deliver alike.

What the callers rely on: a delegation is a task from the actor to a direct report, with the body the templates make of the goal, the acceptance
criteria and the inputs, with the budget the caller names or the most that can be afforded; the refusals are the texts agents are shown."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from orgmcp.dispatch import TaskAssigner
from orgmcp.dispatch.testing import IMPLEMENTATIONS, DispatchWorld, FixedReworkContext
from orgmcp.kernel import OrgError
from orgmcp.templates.testing import static_document_templates

from ._support import grant, implementations, make

TEMPLATES = static_document_templates()


@pytest.fixture(params=implementations(IMPLEMENTATIONS[TaskAssigner]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    made = make(request, tmp_path)
    assert isinstance(made.assigner, TaskAssigner)
    return made


# ------------------------------------------------------------------------------ a delegation is a task


def test_root_delegates_to_any_agent(w: DispatchWorld) -> None:
    task = w.assigner.delegate("root", "ceo", "Write it", "Write the blurb.", "33 words", budget=5)
    assert (task.sender, task.to, task.type, task.title, task.budget) == ("root", "ceo", "task", "Write it", 5)
    assert [m.id for m in w.inbox("ceo")] == [task.id]


def test_the_body_is_the_task_text_of_the_templates(w: DispatchWorld) -> None:
    task = w.assigner.delegate("root", "ceo", "Write it", "Write the blurb.", "33 words", ["/data/in", "/data/more"], budget=5)
    assert task.body == TEMPLATES.task_body("Write the blurb.", "33 words", ["/data/in", "/data/more"]).strip()


def test_a_manager_delegates_to_a_direct_report(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 8)
    task = w.assigner.delegate("ceo", "ceo/eng", "Draft", "Draft it.", "one page", budget=3)
    assert (task.sender, task.to, task.budget) == ("ceo", "ceo/eng", 3)
    assert w.query.budget("ceo") == 5 and w.query.budget("ceo/eng") == 3


def test_the_short_name_of_a_direct_report_is_not_an_address(w: DispatchWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: eng"):
        w.assigner.delegate("ceo", "eng", "Draft", "Draft it.", "one page", budget=1)


def test_the_title_is_stripped_like_that_of_any_message(w: DispatchWorld) -> None:
    assert w.assigner.delegate("root", "ceo", "  Padded  ", "Goal.", "Criteria.", budget=2).title == "Padded"


# ------------------------------------------------------------------------------ who may be given a task


def test_a_manager_cannot_delegate_to_a_sibling_or_to_its_own_parent(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 8)
    with pytest.raises(OrgError) as e:
        w.assigner.delegate("ceo", "ceo/ops/dev", "Draft", "Draft it.", "one page", budget=1)
    assert str(e.value) == "you can only delegate to your direct reports: ceo/eng, ceo/ops, ceo/qa"
    with pytest.raises(OrgError, match="you can only delegate to your direct reports"):
        w.assigner.delegate("ceo/eng", "ceo", "Up", "Up.", "Up.", budget=1)


def test_an_agent_without_reports_is_told_to_hire_one(w: DispatchWorld) -> None:
    with pytest.raises(OrgError) as e:
        w.assigner.delegate("ceo/eng", "ceo/qa", "Draft", "Draft it.", "one page", budget=1)
    assert str(e.value) == "you can only delegate to your direct reports: none (hire one first)"


def test_an_agent_that_does_not_exist_cannot_be_given_a_task(w: DispatchWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        w.assigner.delegate("root", "ghost", "Draft", "Draft it.", "one page", budget=1)


# ------------------------------------------------------------------------------ what a task needs


@pytest.mark.parametrize(("title", "goal", "acceptance"), [("", "g", "a"), ("t", " ", "a"), ("t", "g", "\n"), ("  ", "  ", "  ")])
def test_a_task_needs_a_title_a_goal_and_acceptance_criteria(w: DispatchWorld, title: str, goal: str, acceptance: str) -> None:
    with pytest.raises(OrgError) as e:
        w.assigner.delegate("root", "ceo", title, goal, acceptance, budget=1)
    assert str(e.value) == "a task needs a title, a goal and acceptance criteria"


@pytest.mark.parametrize("budget", [0, -3])
def test_a_task_needs_a_budget_of_at_least_one_run(w: DispatchWorld, budget: int) -> None:
    with pytest.raises(OrgError) as e:
        w.assigner.delegate("root", "ceo", "t", "g", "a", budget=budget)
    assert str(e.value) == "a task needs a budget of at least 1 run"


def test_nothing_is_delivered_when_a_task_is_refused(w: DispatchWorld) -> None:
    with pytest.raises(OrgError):
        w.assigner.delegate("root", "ceo", "", "g", "a", budget=1)
    assert w.inbox("ceo") == [] and w.sent("root") == []


# ------------------------------------------------------------------------------ the budget


def test_root_without_a_budget_gives_the_default_of_the_settings(w: DispatchWorld) -> None:
    assert w.assigner.delegate("root", "ceo", "t", "g", "a").budget == 10
    w.configure("---\nmission: test\ndefault_budget: 4\n---\nrules\n")
    assert w.assigner.delegate("root", "ceo", "t2", "g", "a").budget == 4


def test_a_manager_without_a_budget_gives_what_it_can_afford(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 6)
    assert w.assigner.delegate("ceo", "ceo/eng", "t", "g", "a").budget == 5  # 6 - (0 outstanding + 1)


def test_a_manager_that_cannot_afford_a_delegation_is_told_the_options(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 1)
    with pytest.raises(OrgError, match="you cannot afford this delegation: you have 1 run.*report `blocked`"):
        w.assigner.delegate("ceo", "ceo/eng", "t", "g", "a")


def test_a_manager_cannot_hand_down_what_it_must_keep_in_reserve(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 5)
    with pytest.raises(OrgError) as e:
        w.assigner.delegate("ceo", "ceo/eng", "t", "g", "a", budget=5)
    assert str(e.value) == (
        "not enough budget: you have 5 run(s) and must keep 1 in reserve (one per outstanding delegation, to process its result), "
        "so you can hand down at most 4. Ask your parent for more budget or do less."
    )


# ------------------------------------------------------------------------------ rework


def test_revises_must_be_an_earlier_task_sent_to_the_same_report(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 20)
    first = w.assigner.delegate("ceo", "ceo/eng", "Draft", "Draft it.", "one page", budget=3)
    other = w.assigner.delegate("ceo", "ceo/qa", "Check", "Check it.", "all", budget=3)
    for bad in (other.id, "20260101T000000000001-ceo-aaaa"):
        with pytest.raises(OrgError) as e:
            w.assigner.delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=bad)
        assert str(e.value) == f"revises must be the id of an earlier task you sent to ceo/eng: {bad}"
    again = w.assigner.delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=first.id)
    assert again.revises == first.id and again.type == "task"


def test_a_note_is_not_a_task_to_revise(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 20)
    note = w.sender.send("ceo", "ceo/eng", "fyi")
    with pytest.raises(OrgError, match="revises must be the id of an earlier task you sent to ceo/eng"):
        w.assigner.delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=note.id)


def test_an_ordinary_rework_carries_no_service_fields(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 20)
    first = w.assigner.delegate("ceo", "ceo/eng", "Draft", "Draft it.", "one page", budget=3)
    again = w.assigner.delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=first.id)
    assert (again.service, again.contract, again.playbook) == (None, None, None)


def test_a_rework_of_a_service_request_keeps_its_service_fields(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 20)
    first = w.assigner.delegate("ceo", "ceo/eng", "Draft", "Draft it.", "one page", budget=3)
    rework = FixedReworkContext({first.id: {"service": "weekly-brief", "contract": 3, "playbook": 2}})
    again = w.assigner_with(rework).delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=first.id)
    assert (again.service, again.contract, again.playbook, again.revises) == ("weekly-brief", 3, 2, first.id)


def test_the_rework_fields_are_asked_for_only_when_a_task_is_revised(w: DispatchWorld) -> None:
    asked: list[str] = []

    class Spy(FixedReworkContext):
        def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
            asked.append(revises)
            return super().fields_for(actor, revises)

    w.assigner_with(Spy({})).delegate("root", "ceo", "t", "g", "a", budget=1)
    assert asked == []
