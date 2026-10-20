"""Providers of the ``telemetry`` ports (ARCHITECTURE.md 6.1).

The write side of the event log is shared by every runtime of the process (one file per process and day): the pool, the process name,
the trace scope and the sinks of the roots are ``ProcessResources``; each runtime has its own sink over them, built from its own
settings, ignore list, environment and event clock (the system's; a test fixes it with ``wiring.overriding``).
"""

from __future__ import annotations

from ..kernel import Environment, EventSink, OrgLayout, TraceTap
from ..kernel._system import SystemClock
from ..settings import EventSwitch
from ..snapshots import IgnoreList
from ..telemetry import ArgumentSummarizer, EventRetention, EventSinks, ProcessLabel, TraceScope
from ..telemetry._ports import EventClock
from ..telemetry._retention import FsEventRetention
from ..telemetry._sink import FsEventSink
from ..telemetry._summarize import JsonArgumentSummarizer
from ._builder import Builder
from ._resources import ProcessResources


def register(b: Builder) -> None:
    def resources(b: Builder) -> ProcessResources:
        return b.get(ProcessResources)

    b.provide(
        EventSink,
        lambda b: FsEventSink(
            b.get(OrgLayout), resources(b).event_pool, resources(b).event_pool, b.get(EventSwitch), resources(b).process_label,
            b.get(EventClock), b.get(Environment), b.get(IgnoreList),
        ),
    )
    b.provide(EventClock, lambda b: SystemClock())
    b.provide(TraceTap, lambda b: resources(b).trace_scope)
    b.provide(TraceScope, lambda b: resources(b).trace_scope)
    b.provide(EventSinks, lambda b: resources(b).event_sinks)
    b.provide(ProcessLabel, lambda b: resources(b).process_label)
    b.provide(EventRetention, lambda b: FsEventRetention(b.get(OrgLayout), b.get(EventClock), resources(b).event_pool))
    b.provide(ArgumentSummarizer, lambda b: JsonArgumentSummarizer())
