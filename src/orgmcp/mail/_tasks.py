"""Which tasks are open, derived from the messages (skeleton: red step of A-mail)."""

from __future__ import annotations

from ..kernel import Message
from .api import MailboxReader, TaskQuery


class DerivedTaskQuery(TaskQuery):
    def __init__(self, reader: MailboxReader) -> None:
        raise NotImplementedError

    def open_tasks(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def outstanding(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def blocked_tasks(self, addr: str) -> list[Message]:
        raise NotImplementedError
