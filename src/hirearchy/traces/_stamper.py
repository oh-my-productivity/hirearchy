"""The rules that stamp a trace on a message (moved from ``Org.stamp_trace``)."""

from __future__ import annotations

from ..kernel import ROOT, RUNTIME, Message, norm
from .api import TraceLookup, TraceStamper


class RuleTraceStamper(TraceStamper):
    """Gives a message its trace by the first matching rule: ``given > new > link > open-task > batch > ambiguous``."""

    def __init__(self, lookup: TraceLookup) -> None:
        self._lookup = lookup

    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        if msg.trace:
            return "given", []
        sender = norm(msg.sender)
        if sender == ROOT and msg.type == "task" and not msg.revises:
            msg.trace = msg.id
            return "new", []
        for ref in (msg.reply_to, msg.revises):
            linked = self._lookup.trace_of(sender, ref) if sender != RUNTIME and ref else None
            if linked:
                msg.trace = linked
                return "link", []
        if sender == RUNTIME:
            return "ambiguous", []
        trace, rule, candidates = self._lookup.context_trace(sender)
        msg.trace = trace
        return rule, candidates
