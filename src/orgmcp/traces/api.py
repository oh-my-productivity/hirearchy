"""The public surface of ``traces``: which request trace a message belongs to.

A trace is the id of the task that started a request (the human's task to a top-level agent); every message that follows from it carries
that id in its front matter. ``TraceLookup`` reads what the mailboxes say about traces, ``TraceStamper`` decides the trace of a message
that is about to be delivered.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import Message

__all__ = [
    "TraceLookup",
    "TraceStamper",
]


@runtime_checkable
class TraceLookup(Protocol):
    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        """The trace stamped on message ``msg_id``, looked up in ``addr``'s own four boxes only; None when it is not there, is
        unstamped, does not parse, or ``msg_id`` is empty or is not a plain file name (word characters, dots and dashes)."""
        ...

    def open_task_traces(self, addr: str) -> list[str | None]:
        """The trace of every task ``addr`` received and has not finished (it sent no result, or only a ``blocked`` one), sorted by task
        id; None for a task without a trace. ``[]`` for root, for the runtime and for an address that is not an agent."""
        ...

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        """``(trace, rule, candidates)`` from what ``addr`` is working on: ``("<trace>", "open-task", [])`` when its open tasks all share
        one trace (and none lacks one), else ``("<trace>", "batch", [])`` when the messages of its current batch (``inflight``) have
        exactly one, else ``(None, "ambiguous", <every trace it could be, sorted>)``."""
        ...


@runtime_checkable
class TraceStamper(Protocol):
    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        """Set ``msg.trace`` by the first matching rule and return ``(rule, candidates)``. In order: ``given`` (already set: runtime
        notices about a known task); ``new`` (root sends a task that revises nothing: its own id); ``link`` (it answers, ``reply_to``,
        or reworks, ``revises``, a message of the sender's boxes that has a trace; the runtime never links); ``open-task`` and
        ``batch`` (the sender's context, see ``TraceLookup.context_trace``); else ``ambiguous`` (``trace`` stays None and the
        candidates are returned for the event; the runtime has no context and is always ambiguous with no candidates)."""
        ...
