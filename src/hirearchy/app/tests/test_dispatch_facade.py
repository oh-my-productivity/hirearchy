"""The dispatch slice of the ``Org`` facade: ``can_message``, ``_next_hops``, ``send``, ``delegate``, ``report``, ``_normalize_artifact`` and
``_check_lessons`` behave as they always did (green before and after), and ``send``, ``delegate`` and ``report`` now go through the ports of the
runtime (``facade_sender`` for ``send``, ``task_assigner`` and ``task_reporter``)."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from hirearchy.app import Org
from hirearchy.dispatch import LESSONS_MAX_CHARS, MessageSender, TaskAssigner, TaskReporter
from hirearchy.kernel import Message, OrgError


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    made.hire("ceo", "qa", "Tester", "Test.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_the_routes_of_the_tree(org: Org) -> None:
    assert org.can_message("root", "ceo/eng") and org.can_message("ceo", "root") and org.can_message("ceo/eng", "ceo/qa")
    assert not org.can_message("ceo", "ceo") and not org.can_message("ceo/eng", "root")


def test_the_hops_of_the_next_message(org: Org) -> None:
    assert org._next_hops("root") == 0 and org._next_hops("ceo") == 1
    org.send("root", "ceo", "a task", type="task", budget=3)
    org.begin_run("ceo")
    assert org._next_hops("ceo") == 1  # the batch holds a message of the human: 0 hops, so the next is 1
    org.send("ceo", "ceo/eng", "on", budget=1)
    org.begin_run("ceo/eng")
    assert org._next_hops("ceo/eng") == 2


def test_send_delegate_and_report_make_a_conversation(org: Org) -> None:
    task = org.delegate("root", "ceo", "Work", "Do it.", "Done when it is.", ["/data/in"], budget=5)
    assert (task.type, task.budget, task.sender, task.to) == ("task", 5, "root", "ceo")
    assert org.send("ceo", "root", "question", title="Q").type == "note"
    org.begin_run("ceo")
    result = org.report("ceo", task.id, "done", "Done.")
    assert (result.type, result.status, result.reply_to, result.to) == ("result", "done", task.id, "root")


def test_the_private_skip_flag_keeps_its_name(org: Org) -> None:
    assert org.send("ceo/eng", "root", "x", type="result", _skip_route_check=True).to == "root"
    with pytest.raises(OrgError, match="ceo/eng cannot message root"):
        org.send("ceo/eng", "root", "x")


def test_the_artifact_helper_and_the_lessons_helper_keep_their_names(org: Org) -> None:
    org.write("ceo", "ceo/work/x.md", "a b c")
    assert org._normalize_artifact("ceo", "ceo/work/x.md").startswith("ceo/work/x.md (3 words, modified ")
    task = Message(sender="root", to="ceo", type="task", body="b", id="T1", service="s")
    with pytest.raises(OrgError, match="pass `lessons`"):
        Org._check_lessons(task, "done", None)
    assert org._check_lessons(task, "done", " ok ") == "ok" and LESSONS_MAX_CHARS == 800


# -------------------------------------------------------------------------------------------- through the ports


class Sender(MessageSender):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, dict[str, object]]] = []

    def send(
        self, actor: str, to: str, body: str, *, type: str = "note", title: str = "", reply_to: str | None = None, status: str | None = None,
        budget: int = 0, revises: str | None = None, supersedes: str | None = None, service: str | None = None, contract: int | None = None,
        playbook: int | None = None, feedback: str | None = None, source: str | None = None, criterion: str | None = None, wake: bool = True,
        skip_route_check: bool = False, inherited: str | None = None, acknowledges: str | None = None,
    ) -> Message:
        self.calls.append((actor, to, body, {
            "type": type, "title": title, "reply_to": reply_to, "status": status, "budget": budget, "revises": revises, "supersedes": supersedes,
            "service": service, "contract": contract, "playbook": playbook, "feedback": feedback, "source": source, "criterion": criterion, "wake": wake,
            "skip_route_check": skip_route_check,
        }))
        return Message(sender=actor, to=to, type=type, body=body, id="FROM-THE-PORT")


def test_send_comes_from_the_facade_sender_of_the_runtime_with_the_names_of_the_port(org: Org) -> None:
    fake = Sender()
    use(org, facade_sender=fake)
    assert org.send("ceo", "root", "b", type="result", title="t", reply_to="r", status="done", budget=2, revises="v", supersedes="s", service="svc",
                    contract=3, playbook=4, feedback="accept", source="human", criterion="C1", wake=False, _skip_route_check=True).id == "FROM-THE-PORT"
    assert fake.calls == [("ceo", "root", "b", {
        "type": "result", "title": "t", "reply_to": "r", "status": "done", "budget": 2, "revises": "v", "supersedes": "s", "service": "svc",
        "contract": 3, "playbook": 4, "feedback": "accept", "source": "human", "criterion": "C1", "wake": False, "skip_route_check": True,
    })]
    org.send("ceo", "root", "plain")
    assert fake.calls[1][3]["skip_route_check"] is False and fake.calls[1][3]["type"] == "note" and fake.calls[1][3]["source"] is None
    assert fake.calls[1][3]["criterion"] is None


def test_delegate_comes_from_the_assigner_of_the_runtime(org: Org) -> None:
    calls: list[tuple[object, ...]] = []

    class Assigner(TaskAssigner):
        def delegate(self, actor: str, to: str, title: str, goal: str, acceptance: str, inputs: Any = None, budget: int | None = None,
                     revises: str | None = None, source: str | None = None) -> Message:
            calls.append((actor, to, title, goal, acceptance, inputs, budget, revises, source))
            return Message(sender=actor, to=to, type="task", body="b", id="DELEGATED")

    use(org, task_assigner=Assigner())
    assert org.delegate("root", "ceo", "T", "g", "a", ["/in"], 3, "R", "human").id == "DELEGATED"
    assert calls == [("root", "ceo", "T", "g", "a", ["/in"], 3, "R", "human")]


def test_report_comes_from_the_reporter_of_the_runtime(org: Org) -> None:
    calls: list[tuple[object, ...]] = []

    class Reporter(TaskReporter):
        def report(self, actor: str, task_id: str, status: str, summary: str, artifacts: Any = None, lessons: str | None = None) -> Message:
            calls.append((actor, task_id, status, summary, artifacts, lessons))
            return Message(sender=actor, to="root", type="result", body="b", id="REPORTED")

    use(org, task_reporter=Reporter())
    assert org.report("ceo", "T1", "done", "s", ["a.md"], "l").id == "REPORTED" and calls == [("ceo", "T1", "done", "s", ["a.md"], "l")]


SERVICE_OR_REWORK = (
    "refused: a root task for a service, or a rework, goes through request(...) or delegate(...), which apply the case rules (the contract, the "
    "base, the verdicts). Nothing was sent."
)


def test_org_send_refuses_a_root_service_task_or_rework(org: Org) -> None:
    first = org.delegate("root", "ceo", "Work", "Do it.", "Done when it is.", budget=3)
    sent = len(org.sent("root"))
    for fields in ({"service": "weekly-brief"}, {"revises": first.id}, {"revises": first.id, "source": "human"}):
        with pytest.raises(OrgError) as refusal:
            org.send("root", "ceo", "again", type="task", **fields)  # type: ignore[arg-type]
        assert str(refusal.value) == SERVICE_OR_REWORK
    assert len(org.sent("root")) == sent
    assert org.send("root", "ceo", "a one-off", type="task", budget=1).type == "task"  # every other root message still goes
    assert org.send("root", "ceo", "a note").type == "note"
    org.send("root", "ceo", "runs for you", budget=4)
    assert org.send("ceo", "ceo/eng", "work", type="task", budget=1).type == "task"


def test_the_facade_sender_of_the_runtime_guards_the_message_sender(org: Org) -> None:
    from hirearchy.dispatch import GuardedSender
    from hirearchy.dispatch._guarded import GuardedRootSender

    assert isinstance(org.runtime.facade_sender, GuardedRootSender) and isinstance(org.runtime.facade_sender, GuardedSender)
    assert org.runtime.facade_sender is org.runtime.facade_sender and org.runtime.facade_sender is not org.runtime.message_sender


VERDICT_OR_LINK = (
    "refused: a verdict or a link from root goes through feedback(...), which applies the rules of a case (a delivered request, one answer per "
    "rejection). Nothing was sent."
)


def test_org_send_refuses_a_root_verdict_or_link(org: Org) -> None:
    task = org.delegate("root", "ceo", "Work", "Do it.", "Done when it is.", budget=3)
    sent = len(org.sent("root"))
    for fields in ({"feedback": "reject"}, {"feedback": "accept", "source": "human"}, {"criterion": "C1", "reply_to": task.id}, {"feedback": "reject", "criterion": "C1", "reply_to": task.id}):
        with pytest.raises(OrgError) as refusal:
            org.send("root", "ceo", "words", **fields)  # type: ignore[arg-type]
        assert str(refusal.value) == VERDICT_OR_LINK
    assert len(org.sent("root")) == sent
    assert org.send("root", "ceo", "a plain note", title="fyi").feedback is None  # every other root note still goes
    with pytest.raises(OrgError, match="only root"):  # an agent's verdict is refused by provenance, as before
        org.send("ceo", "root", "words", feedback="reject", criterion="C1", reply_to=task.id)
