"""``BatchRenderer``: a message of a batch, a result followed by the task it answers (moved from ``Org._render_in_context``)."""

from __future__ import annotations

from ..kernel import Message
from ..mail import MailboxReader
from ._ports import ContextRenderer, TaskQuoter, UpstreamTasks


class BatchRenderer(ContextRenderer):
    def __init__(self, mail: MailboxReader, quoter: TaskQuoter, upstream: UpstreamTasks) -> None:
        self._mail = mail
        self._quoter = quoter
        self._upstream = upstream

    def render(self, addr: str, m: Message) -> str:
        raise NotImplementedError("red: C-prompts")
