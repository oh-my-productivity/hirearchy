"""``RuleTaskAssigner``: how it uses its collaborators, in which order it refuses (the texts are in ``test_contract_task_assigner``)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from hirearchy.budget import AllocationPolicy
from hirearchy.dispatch import MessageSender, TaskAssigner
from hirearchy.dispatch._assigner import RuleTaskAssigner
from hirearchy.dispatch.testing import IMPLEMENTATIONS, DispatchWorld, FixedReworkContext
from hirearchy.kernel import Message, OrgError
from hirearchy.templates import DocumentTemplates

from ._support import grant, implementations, make


class Sender(MessageSender):
    """Keeps the arguments of every send."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, str, str], dict[str, object]]] = []

    def send(self, actor: str, to: str, body: str, **kw: object) -> Message:
        self.calls.append(((actor, to, body), kw))
        return Message(sender=actor, to=to, type="task", body=body)


class Policy(AllocationPolicy):
    def __init__(self, default: int = 7) -> None:
        self.default = default
        self.asked: list[str] = []

    def check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        raise AssertionError("the sender checks the allocation, not the assigner")

    def default_budget(self, actor: str) -> int:
        self.asked.append(actor)
        return self.default

    def budget_to_return(self, actor: str, task: Message, status: str) -> int:
        raise AssertionError("not a question of a delegation")


class Templates(DocumentTemplates):
    def org_rules(self, mission: str | None) -> str:
        raise AssertionError

    def charter_body(self, role: str, charter: str) -> str:
        raise AssertionError

    def task_body(self, goal: str, acceptance: str, inputs: Sequence[str]) -> str:
        return f"BODY[{goal}|{acceptance}|{','.join(inputs)}]"

    def result_body(self, summary: str, artifacts: Sequence[str], lessons: str = "") -> str:
        raise AssertionError


@pytest.fixture(params=implementations(IMPLEMENTATIONS[TaskAssigner]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    return make(request, tmp_path)


def over(w: DispatchWorld, sender: Sender, policy: Policy | None = None, rework: FixedReworkContext | None = None) -> RuleTaskAssigner:
    return RuleTaskAssigner(w.agents, w.mail, Templates(), policy or Policy(), rework or FixedReworkContext({}), sender)


def test_the_task_is_sent_through_the_sender_with_the_body_of_the_templates(w: DispatchWorld) -> None:
    sender = Sender()
    over(w, sender).delegate("root", " ceo ", "Title", "Goal", "Criteria", ["/in/a", "/in/b"], 4)
    assert sender.calls == [(("root", "ceo", "BODY[Goal|Criteria|/in/a,/in/b]"), {"type": "task", "title": "Title", "budget": 4, "revises": None, "source": None})]


def test_no_inputs_are_an_empty_list_for_the_templates(w: DispatchWorld) -> None:
    sender = Sender()
    over(w, sender).delegate("root", "ceo", "Title", "Goal", "Criteria", None, 1)
    assert sender.calls[0][0][2] == "BODY[Goal|Criteria|]"


def test_the_budget_not_given_is_the_default_of_the_allocation_policy(w: DispatchWorld) -> None:
    sender, policy = Sender(), Policy(7)
    over(w, sender, policy).delegate("root", "ceo", "Title", "Goal", "Criteria")
    assert policy.asked == ["root"] and sender.calls[0][1]["budget"] == 7


def test_a_budget_that_is_given_does_not_ask_the_policy(w: DispatchWorld) -> None:
    policy = Policy()
    over(w, Sender(), policy).delegate("root", "ceo", "Title", "Goal", "Criteria", budget=2)
    assert policy.asked == []


def test_a_default_below_one_run_is_refused(w: DispatchWorld) -> None:
    sender = Sender()
    with pytest.raises(OrgError, match="a task needs a budget of at least 1 run"):
        over(w, sender, Policy(0)).delegate("root", "ceo", "Title", "Goal", "Criteria")
    assert sender.calls == []


def test_the_rework_fields_are_passed_on_when_a_task_is_revised(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 20)
    first = w.assigner.delegate("ceo", "ceo/eng", "Draft", "Draft it.", "one page", budget=3)
    sender = Sender()
    rework = FixedReworkContext({first.id: {"service": "weekly-brief", "contract": 3, "playbook": 2}})
    over(w, sender, rework=rework).delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=first.id)
    assert sender.calls[0][1] == {
        "type": "task", "title": "Again", "budget": 2, "revises": first.id, "source": None, "service": "weekly-brief", "contract": 3,
        "playbook": 2,
    }


def test_the_order_of_the_refusals(w: DispatchWorld) -> None:
    sender = Sender()
    assigner = over(w, sender)
    with pytest.raises(OrgError, match="no such agent: ghost"):
        assigner.delegate("ceo", "ghost", "", "", "", budget=0)
    with pytest.raises(OrgError, match="you can only delegate to your direct reports"):
        assigner.delegate("ceo", "ceo/ops/dev", "", "", "", budget=0)
    with pytest.raises(OrgError, match="a task needs a title, a goal and acceptance criteria"):
        assigner.delegate("ceo", "ceo/eng", "", "g", "a", budget=0)
    with pytest.raises(OrgError, match="a task needs a budget of at least 1 run"):
        assigner.delegate("ceo", "ceo/eng", "t", "g", "a", budget=0, revises="whatever")
    with pytest.raises(OrgError, match="revises must be the id of an earlier task you sent to ceo/eng: whatever"):
        assigner.delegate("ceo", "ceo/eng", "t", "g", "a", budget=1, revises="whatever")
    assert sender.calls == []
