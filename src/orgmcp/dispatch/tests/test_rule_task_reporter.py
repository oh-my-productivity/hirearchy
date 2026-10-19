"""``RuleTaskReporter``: how it uses its collaborators and in which order it refuses (the texts are in ``test_contract_task_reporter``)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from orgmcp.budget import AllocationPolicy
from orgmcp.dispatch import MessageSender, TaskReporter
from orgmcp.dispatch._protocols import ArtifactNormalizer, LessonsCheck
from orgmcp.dispatch._reporter import RuleTaskReporter
from orgmcp.dispatch.testing import IMPLEMENTATIONS, DispatchWorld
from orgmcp.kernel import Message, OrgError
from orgmcp.templates import DocumentTemplates

from ._support import RED, assigned, implementations, make

pytestmark = RED


class Sender(MessageSender):
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, str, str], dict[str, object]]] = []

    def send(self, actor: str, to: str, body: str, **kw: object) -> Message:
        self.calls.append(((actor, to, body), kw))
        return Message(sender=actor, to=to, type="result", body=body)


class Policy(AllocationPolicy):
    def __init__(self, returns: int = 4) -> None:
        self.returns = returns
        self.asked: list[tuple[str, str, str]] = []

    def check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        raise AssertionError("the sender checks the allocation, not the reporter")

    def default_budget(self, actor: str) -> int:
        raise AssertionError("not a delegation")

    def budget_to_return(self, actor: str, task: Message, status: str) -> int:
        self.asked.append((actor, task.id, status))
        return self.returns


class Templates(DocumentTemplates):
    def org_rules(self, mission: str | None) -> str:
        raise AssertionError

    def charter_body(self, role: str, charter: str) -> str:
        raise AssertionError

    def task_body(self, goal: str, acceptance: str, inputs: Sequence[str]) -> str:
        raise AssertionError

    def result_body(self, summary: str, artifacts: Sequence[str], lessons: str = "") -> str:
        return f"RESULT[{summary}|{';'.join(artifacts)}|{lessons}]"


class Lessons(LessonsCheck):
    def __init__(self, log: list[str]) -> None:
        self.log = log

    def check(self, task: Message, status: str, lessons: str | None) -> str:
        self.log.append(f"lessons {task.id} {status} {lessons!r}")
        if lessons == "refuse":
            raise OrgError("lessons refused")
        return f"L:{lessons}"


class Artifacts(ArtifactNormalizer):
    def __init__(self, log: list[str]) -> None:
        self.log = log

    def normalize(self, actor: str, path: str, since: str = "") -> str:
        self.log.append(f"artifact {actor} {path}")
        if path == "refuse":
            raise OrgError("artifact refused")
        return f"<{path}|{since}>"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[TaskReporter]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    return make(request, tmp_path)


class Over:
    def __init__(self, w: DispatchWorld, policy: Policy | None = None) -> None:
        self.log: list[str] = []
        self.sender = Sender()
        self.policy = policy or Policy()
        self.reporter = RuleTaskReporter(
            w.agents, w.mail, w.tasks, Templates(), self.policy, Lessons(self.log), Artifacts(self.log), self.sender,
        )


def test_the_result_is_sent_through_the_sender_without_the_route_check(w: DispatchWorld) -> None:
    task = assigned(w)
    o = Over(w)
    o.reporter.report(" ceo ", task.id, "done", "Summary.", ["a.md", "b.md"], "learned")
    assert o.sender.calls == [(
        ("ceo", "root", f"RESULT[Summary.|<a.md|{task.created}>;<b.md|{task.created}>|L:learned]"),
        {"type": "result", "title": "Work", "reply_to": task.id, "status": "done", "supersedes": None, "skip_route_check": True, "budget": 4},
    )]


def test_the_budget_is_that_of_the_allocation_policy_for_this_task_and_status(w: DispatchWorld) -> None:
    task = assigned(w)
    o = Over(w, Policy(9))
    o.reporter.report("ceo", task.id, "failed", "Summary.")
    assert o.policy.asked == [("ceo", task.id, "failed")] and o.sender.calls[0][1]["budget"] == 9


def test_a_blocked_result_that_is_reported_again_names_the_one_it_supersedes(w: DispatchWorld) -> None:
    task = assigned(w)
    first = w.reporter.report("ceo", task.id, "blocked", "Waiting.")
    o = Over(w)
    o.reporter.report("ceo", task.id, "done", "Data came.")
    assert o.sender.calls[0][1]["supersedes"] == first.id


def test_no_artifacts_and_no_lessons_are_an_empty_list_and_a_text(w: DispatchWorld) -> None:
    task = assigned(w)
    o = Over(w)
    o.reporter.report("ceo", task.id, "done", "Summary.", None, None)
    assert o.sender.calls[0][0][2] == "RESULT[Summary.||L:None]"


def test_the_lessons_are_checked_before_the_artifacts_and_both_before_the_send(w: DispatchWorld) -> None:
    task = assigned(w)
    o = Over(w)
    o.reporter.report("ceo", task.id, "done", "Summary.", ["a.md"], "x")
    assert o.log == [f"lessons {task.id} done 'x'", "artifact ceo a.md"]


def test_a_refused_lesson_stops_the_report_before_the_artifacts(w: DispatchWorld) -> None:
    task = assigned(w)
    o = Over(w)
    with pytest.raises(OrgError, match="lessons refused"):
        o.reporter.report("ceo", task.id, "done", "Summary.", ["a.md"], "refuse")
    assert o.sender.calls == [] and not any(line.startswith("artifact") for line in o.log)


def test_a_refused_artifact_stops_the_report(w: DispatchWorld) -> None:
    task = assigned(w)
    o = Over(w)
    with pytest.raises(OrgError, match="artifact refused"):
        o.reporter.report("ceo", task.id, "done", "Summary.", ["a.md", "refuse", "c.md"])
    assert o.sender.calls == [] and o.policy.asked == []


def test_a_report_that_is_final_already_is_refused_before_the_lessons(w: DispatchWorld) -> None:
    task = assigned(w)
    w.reporter.report("ceo", task.id, "done", "Done.")
    o = Over(w)
    with pytest.raises(OrgError, match="already reported done"):
        o.reporter.report("ceo", task.id, "done", "Again.", None, "x")
    assert o.log == [] and o.sender.calls == []


def test_the_status_and_the_task_are_checked_before_the_lessons(w: DispatchWorld) -> None:
    o = Over(w)
    with pytest.raises(OrgError, match="status must be one of"):
        o.reporter.report("ceo", "x", "bogus", "s", None, "x")
    with pytest.raises(OrgError, match="no task x assigned to you"):
        o.reporter.report("ceo", "x", "done", "s", None, "x")
    assert o.log == []
