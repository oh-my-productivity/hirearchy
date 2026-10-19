"""An agent answers a task it was given (moved from ``Org.report``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..kernel import RESULT_STATUSES, Message, OrgError, latest_results
from ..mail import MailboxReader, TaskQuery
from ..templates import DocumentTemplates
from ._protocols import ArtifactNormalizer, LessonsCheck
from .api import MessageSender, TaskReporter


class RuleTaskReporter(TaskReporter):
    """The task must be assigned to the reporter; ``done`` and ``failed`` are final; ``blocked`` can be reported again."""

    def __init__(
        self, agents: AgentDirectory, mail: MailboxReader, tasks: TaskQuery, templates: DocumentTemplates, allocation: AllocationPolicy,
        lessons: LessonsCheck, artifacts: ArtifactNormalizer, sender: MessageSender,
    ) -> None:
        self._agents = agents
        self._mail = mail
        self._tasks = tasks
        self._templates = templates
        self._allocation = allocation
        self._lessons = lessons
        self._artifacts = artifacts
        self._sender = sender

    def report(
        self, actor: str, task_id: str, status: str, summary: str, artifacts: Sequence[str] | None = None, lessons: str | None = None,
    ) -> Message:
        actor = self._agents.require(actor)
        if status not in RESULT_STATUSES:
            raise OrgError(f"status must be one of {RESULT_STATUSES}")
        task = self._mail.find_received(actor, task_id)
        if task is None or task.type != "task":
            open_ids = ", ".join(t.id for t in self._tasks.open_tasks(actor)) or "none"
            raise OrgError(f"no task {task_id} assigned to you. Your open tasks: {open_ids}")
        prior = latest_results(self._mail.sent(actor)).get(task_id)
        if prior is not None and prior.status != "blocked":
            raise OrgError(
                f"task {task_id} was already reported {prior.status}, and {prior.status} is final (rule 6): it cannot be "
                "reported again or changed by a note. Only a task reported `blocked` can be reported again. If you have "
                "information for whoever assigned it, use `send`, as information only: a note does not change the "
                "task's outcome and must not claim that criteria are met."
            )
        lessons = self._lessons.check(task, status, lessons)
        arts = [self._artifacts.normalize(actor, a, task.created) for a in (artifacts or [])]
        body = self._templates.result_body(summary, arts, lessons)
        return self._sender.send(
            actor, task.sender, body, type="result", title=task.title,
            reply_to=task.id, status=status, supersedes=prior.id if prior else None, skip_route_check=True,
            budget=self._allocation.budget_to_return(actor, task, status),
        )
