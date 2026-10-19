"""Which request trace a message belongs to (traces).

The bodies call the ports of ``self.runtime`` (step B-traces; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from ..kernel import Message
from .runtime import OrgRuntime


class TracesMixin:
    """Which request trace a message belongs to (traces)."""

    runtime: OrgRuntime

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        """The trace stamped on message ``msg_id``, looked up in ``addr``'s own boxes (None: not there or unstamped)."""
        return self.runtime.trace_lookup.trace_of(addr, msg_id)

    def open_task_traces(self, addr: str) -> list[str | None]:
        """Traces of the tasks ``addr`` received and has not finished (no result, or only a ``blocked`` one)."""
        return self.runtime.trace_lookup.open_task_traces(addr)

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        """(trace, rule, candidates) from what ``addr`` is working on: rule 3 (its open tasks all share one trace),
        else rule 4 (its current batch has exactly one), else (None, "ambiguous", every trace it could be)."""
        return self.runtime.trace_lookup.context_trace(addr)

    def stamp_trace(self, msg: Message) -> tuple[str, list[str]]:
        """Set ``msg.trace`` (first matching rule wins) and return (rule, candidates). Rules:

        ``given`` already set (runtime notices about a known task); ``new`` root sends a task without ``revises``: its
        own id; ``link`` it answers (``reply_to``) or reworks (``revises``) a message that has a trace; ``open-task``
        the sender's unfinished tasks share one trace; ``batch`` the sender's current batch has one; else
        ``ambiguous`` (``trace`` stays None; the candidates are returned for the event).
        """
        return self.runtime.trace_stamper.stamp(msg)
