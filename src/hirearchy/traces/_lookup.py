"""The lookup of traces in the mailboxes (moved from ``Org.trace_of``, ``open_task_traces`` and ``context_trace``)."""

from __future__ import annotations

from ..kernel import ROOT, RUNTIME, latest_results, norm
from ..mail import MailboxReader, still_open
from ._ports import AgentPresence
from .api import TraceLookup


class MailboxTraceLookup(TraceLookup):
    """What the mailboxes of an agent say about traces."""

    def __init__(self, mail: MailboxReader, agents: AgentPresence) -> None:
        self._mail = mail
        self._agents = agents

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        if not msg_id:
            return None
        found = self._mail.find_anywhere(addr, msg_id)  # by file name in the four boxes of ``addr``; None for an id that is a path
        return found.trace if found else None

    def open_task_traces(self, addr: str) -> list[str | None]:
        a = norm(addr)
        if a in (ROOT, RUNTIME) or not self._agents.exists(a):
            return []
        latest = latest_results(self._mail.sent(a))
        received = self._mail.received(a)
        return [t.trace for t in received if t.type == "task" and still_open(t, latest.get(t.id), received)]

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        a = norm(addr)
        open_traces = self.open_task_traces(a)
        distinct = {t for t in open_traces if t}
        if len(distinct) == 1 and None not in open_traces:
            return next(iter(distinct)), "open-task", []
        batch = {m.trace for m in self._mail.messages(a, "inflight")} if a not in (ROOT, RUNTIME) and self._agents.exists(a) else set()
        batch_distinct = {t for t in batch if t}
        if len(batch_distinct) == 1:
            return next(iter(batch_distinct)), "batch", []
        return None, "ambiguous", sorted(distinct | batch_distinct)
