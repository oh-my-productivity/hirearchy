"""Providers of the ``observability`` ports (ARCHITECTURE.md 6.1), and the same objects over the runtime in force for the legacy functions.

The first half of the package (events, traces, metrics) is wired here; ``now``, ``check`` and the text of the views come with C-obs-2, which adds the
runtime fields (``test_runtime_fields`` takes all of 3.31 as that step). Until then the ports are built by a ``Builder`` and by ``*_of(runtime)``.

``event_queries_of``, ``trace_queries_of``, ``metric_queries_of``, ``trace_derivers_of``, ``message_history_of`` and ``run_collection_of`` serve the
functions of ``observe.py`` that are still there (the views' text, ``now_view``, ``check``, the dashboard): they are handed an ``Org`` whose
``runtime`` tests replace (the clock, the processes) and the dashboard's lenient ``Org`` replaces the mailboxes of, so each call builds the objects
over the ports the runtime has *now*, as the functions they replace read them through the ``Org``. They go when the legacy functions do.

The second half of ``observe.py`` also needs a few pure helpers of the package that are not public (``cap``, ``iso``, ``plain``, ``matcher``,
``Msg``): it reaches them here, since only the composition root may import a private module (it goes with ``observe.py``, C-obs-2).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..agents import AgentDirectory
from ..eventlog import EventFollowers, EventReader
from ..kernel import Clock
from ..mail import MailboxReader, MessageIndex
from ..observability import EventQueries, MetricQueries, TraceQueries
from ..observability._derive import LogTraceDerivers
from ..observability._events import LogEventQueries
from ..observability._history import IndexedMessageHistory
from ..observability._messages import Msg as Msg  # re-exported for observe.py
from ..observability._messages import build_messages as build_messages  # re-exported for observe.py
from ..observability._metrics import DerivedMetricQueries
from ..observability._ports import MessageHistory, RunCollection, TraceDerivers
from ..observability._runs import RunCollector
from ..observability._runs import RunRec as RunRec  # re-exported for observe.py
from ..observability._runs import run_events as run_events  # re-exported for observe.py
from ..observability._trace import READ_ONLY_TOOLS as READ_ONLY_TOOLS  # re-exported for observe.py
from ..observability._trace import DerivedTraceQueries
from ..observability._trace import run_window as run_window  # re-exported for observe.py
from ..observability._util import cap as cap  # re-exported for observe.py
from ..observability._util import iso as iso  # re-exported for observe.py
from ..observability._util import matcher as matcher  # re-exported for observe.py
from ..observability._util import plain as plain  # re-exported for observe.py
from ..runs import RunLogReader, RunRegistry
from ._builder import Builder
from ._lazy import PortResolver
from .runtime import OrgRuntime
from .wire_stalls import RuntimePorts


def event_queries(b: PortResolver) -> LogEventQueries:
    """The event queries over the event files, the followers and the clock of ``b``."""
    return LogEventQueries(b.get(EventReader), b.get(EventFollowers), b.get(Clock))


def message_history(b: PortResolver) -> MessageHistory:
    """The history of the messages from the index of ``b``."""
    return IndexedMessageHistory(b.get(MessageIndex))


def trace_derivers(b: PortResolver) -> TraceDerivers:
    """The derivation of a message's trace over the run logs of ``b``."""
    return LogTraceDerivers(b.get(RunLogReader))


def run_collection(b: PortResolver) -> RunCollection:
    """The collection of runs over the run logs, registry, agents, mailboxes and event files of ``b``."""
    return RunCollector(b.get(RunLogReader), b.get(RunRegistry), b.get(AgentDirectory), b.get(MailboxReader), b.get(EventReader))


def trace_queries(b: PortResolver) -> DerivedTraceQueries:
    """The trace of a request over the messages, run logs, events and agents of ``b``."""
    return DerivedTraceQueries(message_history(b), trace_derivers(b), b.get(EventReader), run_collection(b), b.get(AgentDirectory), b.get(Clock))


def metric_queries(b: PortResolver) -> DerivedMetricQueries:
    """The metrics over the events, runs and messages of ``b``."""
    return DerivedMetricQueries(b.get(EventReader), run_collection(b), message_history(b), b.get(Clock))


def register(b: Builder) -> None:
    b.provide(EventQueries, event_queries)
    b.provide(TraceQueries, trace_queries)
    b.provide(MetricQueries, metric_queries)


# ------------------------------------------------------------------------------ the legacy functions' objects


def event_queries_of(runtime: OrgRuntime) -> EventQueries:
    """``EventQueries`` over the ports ``runtime`` has now."""
    return event_queries(RuntimePorts(runtime))


class SleepingClock(Clock):
    """``clock`` that sleeps by the function it was given (``observe.follow_events`` has always taken one)."""

    def __init__(self, clock: Clock, sleep: Callable[[float], None]) -> None:
        self._clock, self._sleep = clock, sleep

    def now(self) -> datetime:
        return self._clock.now()

    def time(self) -> float:
        return self._clock.time()

    def monotonic(self) -> float:
        return self._clock.monotonic()

    def sleep(self, seconds: float) -> None:
        self._sleep(seconds)


def event_queries_sleeping(runtime: OrgRuntime, sleep: Callable[[float], None]) -> EventQueries:
    """``EventQueries`` over the ports ``runtime`` has now that waits between polls with ``sleep`` (``follow_events``)."""
    return LogEventQueries(runtime.event_reader, runtime.event_followers, SleepingClock(runtime.clock, sleep))


def trace_queries_of(runtime: OrgRuntime) -> TraceQueries:
    """``TraceQueries`` over the ports ``runtime`` has now."""
    return trace_queries(RuntimePorts(runtime))


def metric_queries_of(runtime: OrgRuntime) -> MetricQueries:
    """``MetricQueries`` over the ports ``runtime`` has now."""
    return metric_queries(RuntimePorts(runtime))


def message_history_of(runtime: OrgRuntime) -> MessageHistory:
    """``MessageHistory`` over the message index ``runtime`` has now."""
    return message_history(RuntimePorts(runtime))


def trace_derivers_of(runtime: OrgRuntime) -> TraceDerivers:
    """``TraceDerivers`` over the run logs ``runtime`` has now."""
    return trace_derivers(RuntimePorts(runtime))


def run_collection_of(runtime: OrgRuntime) -> RunCollection:
    """``RunCollection`` over the ports ``runtime`` has now."""
    return run_collection(RuntimePorts(runtime))
