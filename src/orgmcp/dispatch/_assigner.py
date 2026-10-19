"""A manager gives a task to a direct report. Skeleton: RED."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..kernel import Message
from ..mail import MailboxReader
from ..templates import DocumentTemplates
from .api import MessageSender, ReworkContext, TaskAssigner


class RuleTaskAssigner(TaskAssigner):
    """Direct reports only; a title, a goal and acceptance criteria; a budget of at least one run."""

    def __init__(
        self, agents: AgentDirectory, mail: MailboxReader, templates: DocumentTemplates, allocation: AllocationPolicy,
        rework: ReworkContext, sender: MessageSender,
    ) -> None:
        self._agents = agents
        self._mail = mail
        self._templates = templates
        self._allocation = allocation
        self._rework = rework
        self._sender = sender

    def delegate(
        self, actor: str, to: str, title: str, goal: str, acceptance: str, inputs: Sequence[str] | None = None,
        budget: int | None = None, revises: str | None = None,
    ) -> Message:
        raise NotImplementedError
