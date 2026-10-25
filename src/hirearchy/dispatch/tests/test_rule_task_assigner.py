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
    assert sender.calls == [(("root", "ceo", "BODY[Goal|Criteria|/in/a,/in/b]"), {"type": "task", "title": "Title", "budget": 4, "revises": None, "source": None, "inherited": None})]


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
        "type": "task", "title": "Again", "budget": 2, "revises": first.id, "source": None, "inherited": None, "service": "weekly-brief", "contract": 3,
        "playbook": 2,
    }


def test_delegate_passes_the_inherited_tier(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 20)
    first = w.assigner.delegate("ceo", "ceo/eng", "Draft", "Draft it.", "one page", budget=3)
    sender = Sender()
    rework = FixedReworkContext({first.id: {"source": "human"}})
    over(w, sender, rework=rework).delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=first.id)
    assert sender.calls[0][1] == {"type": "task", "title": "Again", "budget": 2, "revises": first.id, "source": None, "inherited": "human"}


class FailingContext(FixedReworkContext):
    """A ``ReworkContext`` whose mailboxes cannot be read."""

    def __init__(self, error: Exception) -> None:
        super().__init__({})
        self._error = error

    def work_tier(self, actor: str) -> str | None:
        raise self._error


def fresh(w: DispatchWorld, actor: str, to: str, rework: FixedReworkContext) -> dict[str, object]:
    sender = Sender()
    over(w, sender, rework=rework).delegate(actor, to, "Draft", "Draft it.", "one page", budget=2)
    return sender.calls[0][1]


def test_an_agents_fresh_delegation_passes_the_tier_of_its_work(w: DispatchWorld) -> None:
    """F-E6-7 (D-E6-5): a delegation without ``revises`` carries ``inherited=<work_tier>`` for an agent."""
    grant(w, "root", "ceo", 20)
    assert fresh(w, "ceo", "ceo/eng", FixedReworkContext({}, {"ceo": "human"})) == {
        "type": "task", "title": "Draft", "budget": 2, "revises": None, "source": None, "inherited": "human",
    }


def test_roots_fresh_delegation_passes_no_tier_whatever_the_context_says(w: DispatchWorld) -> None:
    assert fresh(w, "root", "ceo", FixedReworkContext({}, {"root": "human", "ceo": "human"}))["inherited"] is None


@pytest.mark.parametrize("error", [OrgError("unreadable"), OSError("unreadable")], ids=["OrgError", "OSError"])
def test_a_context_that_cannot_read_gives_a_delegation_without_a_tier(w: DispatchWorld, error: Exception) -> None:
    grant(w, "root", "ceo", 20)
    assert fresh(w, "ceo", "ceo/eng", FailingContext(error))["inherited"] is None


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


USE_REQUEST = (
    "refused: {revises} is a request for the service `weekly-brief`: send it back with request(service=\"weekly-brief\", inputs=..., "
    "revises=\"{revises}\", source=...) (CLI: hirearchy request weekly-brief --revises {revises}) so the rework stays in its case under the "
    "contract (and names its base when a relayed rework changed the delivery). Nothing was sent."
)


def test_root_delegate_revising_a_service_request_is_refused_use_request(w: DispatchWorld) -> None:
    first = w.assigner.delegate("root", "ceo", "Draft", "Draft it.", "one page", budget=3)
    sender = Sender()
    rework = FixedReworkContext({first.id: {"service": "weekly-brief", "contract": 3, "playbook": 2}})
    with pytest.raises(OrgError) as refusal:
        over(w, sender, rework=rework).delegate("root", "ceo", "Again", "Again.", "better", budget=2, revises=first.id, source="human")
    assert str(refusal.value) == USE_REQUEST.format(revises=first.id) and sender.calls == []


def test_root_delegate_revising_an_ordinary_task_or_an_agent_revising_a_service_task_is_not_refused(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 20)
    root_first = w.assigner.delegate("root", "ceo", "Draft", "Draft it.", "one page", budget=3)
    sender = Sender()
    over(w, sender).delegate("root", "ceo", "Again", "Again.", "better", budget=2, revises=root_first.id)
    first = w.assigner.delegate("ceo", "ceo/eng", "Draft", "Draft it.", "one page", budget=3)
    rework = FixedReworkContext({first.id: {"service": "weekly-brief", "contract": 3, "playbook": 2}})
    over(w, sender, rework=rework).delegate("ceo", "ceo/eng", "Again", "Again.", "better", budget=2, revises=first.id)
    assert len(sender.calls) == 2


def test_the_use_request_refusal_comes_after_the_revises_check(w: DispatchWorld) -> None:
    rework = FixedReworkContext({"nope": {"service": "weekly-brief"}})
    with pytest.raises(OrgError, match="revises must be the id of an earlier task you sent to ceo: nope"):
        over(w, Sender(), rework=rework).delegate("root", "ceo", "Again", "Again.", "better", budget=2, revises="nope")
