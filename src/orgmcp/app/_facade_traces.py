"""Which request trace a message belongs to (traces).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

import re

from ..kernel import latest_results, Message, ROOT, RUNTIME


class TracesMixin:
    """Which request trace a message belongs to (traces)."""

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        """The trace stamped on message ``msg_id``, looked up in ``addr``'s own boxes (None: not there or unstamped)."""
        if not msg_id or not re.fullmatch(r"[\w.\-]+", str(msg_id)):
            return None
        d = self.dir(addr)
        for box in ("inbox", "inflight", "read", "sent"):
            p = d / box / f"{msg_id}.md"
            if p.is_file():
                try:
                    return Message.load(p).trace
                except Exception:  # noqa: BLE001
                    return None
        return None

    def open_task_traces(self, addr: str) -> list[str | None]:
        """Traces of the tasks ``addr`` received and has not finished (no result, or only a ``blocked`` one)."""
        a = self.norm(addr)
        if a in (ROOT, RUNTIME) or not self.exists(a):
            return []
        latest = latest_results(self.sent(a))
        return [
            t.trace for t in self.received(a)
            if t.type == "task" and ((r := latest.get(t.id)) is None or r.status == "blocked")
        ]

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        """(trace, rule, candidates) from what ``addr`` is working on: rule 3 (its open tasks all share one trace),
        else rule 4 (its current batch has exactly one), else (None, "ambiguous", every trace it could be)."""
        a = self.norm(addr)
        open_traces = self.open_task_traces(a)
        distinct = {t for t in open_traces if t}
        if len(distinct) == 1 and None not in open_traces:
            return next(iter(distinct)), "open-task", []
        batch = {m.trace for m in self.messages(a, "inflight")} if a not in (ROOT, RUNTIME) and self.exists(a) else set()
        batch_distinct = {t for t in batch if t}
        if len(batch_distinct) == 1:
            return next(iter(batch_distinct)), "batch", []
        return None, "ambiguous", sorted(distinct | batch_distinct)

    def stamp_trace(self, msg: Message) -> tuple[str, list[str]]:
        """Set ``msg.trace`` (first matching rule wins) and return (rule, candidates). Rules:

        ``given`` already set (runtime notices about a known task); ``new`` root sends a task without ``revises``: its
        own id; ``link`` it answers (``reply_to``) or reworks (``revises``) a message that has a trace; ``open-task``
        the sender's unfinished tasks share one trace; ``batch`` the sender's current batch has one; else
        ``ambiguous`` (``trace`` stays None; the candidates are returned for the event).
        """
        if msg.trace:
            return "given", []
        sender = self.norm(msg.sender)
        if sender == ROOT and msg.type == "task" and not msg.revises:
            msg.trace = msg.id
            return "new", []
        for ref in (msg.reply_to, msg.revises):
            linked = self.trace_of(sender, ref) if sender != RUNTIME else None
            if linked:
                msg.trace = linked
                return "link", []
        if sender == RUNTIME:
            return "ambiguous", []
        trace, rule, candidates = self.context_trace(sender)
        msg.trace = trace
        return rule, candidates
