"""The second half of the package built over the ports of the runtime of a scenario organization (what ``app.wire_observability`` does for the runtime)."""

from __future__ import annotations

import json
from typing import Any

from hirearchy.observability._checks import (
    BudgetConserved,
    FileIntegrityChecks,
    InflightAccounted,
    JudgedLiveRuns,
    MessagesIntact,
    PidfileSane,
    RunsAccounted,
    SeqGapless,
)
from hirearchy.observability._derive import LogTraceDerivers
from hirearchy.observability._dispatch import AgentTargetedEvents, ViewDispatcher
from hirearchy.observability._events import LogEventQueries
from hirearchy.observability._files import FsMailboxFiles, FsSchedulerPidFile
from hirearchy.observability._history import IndexedMessageHistory
from hirearchy.observability._metrics import DerivedMetricQueries
from hirearchy.observability._now import (
    BatchRunsInFlight,
    EventSchedulerReport,
    FileNowQueries,
    LoggedRecentEvents,
    MailInflightBatches,
    MailRootDesk,
    ReasonedQueue,
)
from hirearchy.observability._render import TextObservabilityRenderer
from hirearchy.observability._runs import RunCollector
from hirearchy.observability._trace import DerivedTraceQueries
from hirearchy.observability._util import plain

__all__ = ["Second", "dump"]


def dump(data: object) -> str:
    """What ``cli obs ... --json`` prints."""
    return json.dumps(plain(data), indent=2, default=str) + "\n"


class Second:
    """Every part of ``now``, ``check`` and the text, made over ``rt`` (the runtime of the scenario organization)."""

    def __init__(self, rt: Any) -> None:
        history = IndexedMessageHistory(rt.message_index)
        derivers = LogTraceDerivers(rt.run_log_reader)
        collector = RunCollector(rt.run_log_reader, rt.run_registry, rt.agents, rt.mailbox, rt.event_reader)
        self.index = rt.message_index
        self.scheduler = EventSchedulerReport(rt.scheduler_status, rt.exit_marker, rt.event_reader)
        self.files = FsMailboxFiles(rt.paths)
        self.batches = MailInflightBatches(rt.agents, rt.mailbox, self.files, rt.message_index)
        self.flight = BatchRunsInFlight(self.batches, rt.run_registry, rt.run_log_reader, history, derivers)
        self.queue = ReasonedQueue(rt.agents, rt.mailbox, rt.pause_store, rt.budget_query, self.files)
        self.recent = LoggedRecentEvents(rt.event_reader)
        self.desk = MailRootDesk(rt.human_queue, rt.task_query)
        self.now = FileNowQueries(rt.settings, self.scheduler, self.flight, self.queue, self.recent, self.desk, rt.clock)
        self.live = JudgedLiveRuns(rt.orphan_judge)
        self.messages = MessagesIntact(rt.paths, rt.agents)
        self.budget = BudgetConserved(rt.agents, rt.budget_query, rt.run_log_reader, rt.retired_archive)
        self.inflight = InflightAccounted(rt.agents, self.files, rt.run_registry, self.live, rt.scheduler_status)
        self.runs = RunsAccounted(rt.event_reader, rt.run_registry, self.live, rt.agents, rt.run_log_reader)
        self.seq = SeqGapless(rt.event_reader)
        self.pidfile = PidfileSane(FsSchedulerPidFile(rt.paths), rt.scheduler_status)
        self.parts = [self.messages, self.budget, self.inflight, self.runs, self.seq, self.pidfile]
        self.checks = FileIntegrityChecks(rt.message_index, self.parts, rt.clock)
        self.renderer = TextObservabilityRenderer()
        events = LogEventQueries(rt.event_reader, rt.event_followers, rt.clock)
        traces = DerivedTraceQueries(history, derivers, rt.event_reader, collector, rt.agents, rt.clock)
        metrics = DerivedMetricQueries(rt.event_reader, collector, history, rt.clock)
        self.targeted = AgentTargetedEvents(events, rt.agents, rt.event_reader)
        self.text = ViewDispatcher(self.targeted, traces, metrics, self.now, self.checks, self.renderer)
