"""Which tasks are open, derived from the messages: nothing is stored (ARCHITECTURE.md: state is derived, never stored)."""

from __future__ import annotations

from ..kernel import Message, latest_results, norm
from .api import MailboxReader, TaskQuery


class DerivedTaskQuery(TaskQuery):
    """The three views of an agent's tasks, computed from what its mailbox reader lists."""

    def __init__(self, reader: MailboxReader) -> None:
        self._reader = reader

    def open_tasks(self, addr: str) -> list[Message]:
        a = norm(addr)
        answered = {m.reply_to for m in self._reader.sent(a) if m.type == "result"}
        return [m for m in self._reader.received(a) if m.type == "task" and m.id not in answered]

    def outstanding(self, addr: str) -> list[Message]:
        a = norm(addr)
        answered = {m.reply_to for m in self._reader.received(a) if m.type == "result"}
        return [m for m in self._reader.sent(a) if m.type == "task" and m.id not in answered]

    def blocked_tasks(self, addr: str) -> list[Message]:
        """Tasks assigned to ``addr`` whose latest result is ``blocked``: answered, but they may be reported again."""
        latest = latest_results(self._reader.sent(addr))
        return [
            t for t in self._reader.received(addr) if t.type == "task" and (r := latest.get(t.id)) and r.status == "blocked"
        ]
