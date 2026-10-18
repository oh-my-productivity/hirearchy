"""RED skeleton (B-traces): the rules that stamp a trace on a message."""

from __future__ import annotations

from ..kernel import Message
from .api import TraceLookup, TraceStamper


class RuleTraceStamper(TraceStamper):
    """Gives a message its trace by the first matching rule."""

    def __init__(self, lookup: TraceLookup) -> None:
        self._lookup = lookup

    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        raise NotImplementedError("red: B-traces")
