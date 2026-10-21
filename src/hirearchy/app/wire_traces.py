"""Providers of the ``traces`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..mail import MailboxReader
from ..traces import TraceLookup, TraceStamper
from ..traces._lookup import MailboxTraceLookup
from ..traces._stamper import RuleTraceStamper
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(TraceLookup, lambda b: MailboxTraceLookup(b.get(MailboxReader), b.get(AgentDirectory)))
    b.provide(TraceStamper, lambda b: RuleTraceStamper(b.get(TraceLookup)))
