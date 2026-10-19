"""An agent answers a task it was given. Skeleton: RED."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..kernel import Message
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
        raise NotImplementedError
