"""What is happening right now: the scheduler, the runs in flight, what is queued and why, the recent errors, what waits for root."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..agents import AgentDirectory
from ..attention import HumanQueue
from ..budget import BudgetQuery
from ..daemon import ExitMarker, SchedulerStatus
from ..eligibility import PauseStore
from ..eventlog import EventFile, EventReader
from ..kernel import ROOT, Clock, JsonObject, aware, clip_line, parse_time, stamp_of
from ..mail import MailboxReader, MessageIndex, TaskQuery
from ..runs import RunLogReader, RunRegistry
from ..settings import OrgSettings
from ._ports import (
    BatchItem,
    FlightReport,
    InflightBatches,
    MailboxFiles,
    MessageHistory,
    QueueReport,
    RecentEvents,
    RootDesk,
    SchedulerReport,
    TraceDeriver,
    TraceDerivers,
)
from ._pure import is_error
from ._util import iso
from .api import NowQueries

ERROR_WINDOW = timedelta(minutes=15)


class EventSchedulerReport(SchedulerReport):
    """The state of the scheduler from the status; while it runs, its mode, uptime and heartbeat from its event file; else how the last one exited, from
    the last three event files, else from the exit marker."""

    def __init__(self, status: SchedulerStatus, marker: ExitMarker, events: EventReader) -> None:
        self._status, self._marker, self._events = status, marker, events

    def _files(self) -> list[EventFile]:
        """Every scheduler event file, newest process first."""
        return sorted((f for f in self._events.files() if f.proc == "scheduler"), key=lambda f: (f.start_ms, str(f.path)), reverse=True)

    def info(self, now: datetime) -> JsonObject:
        st = self._status.state()
        info: JsonObject = {"state": st.state, "pid": st.pid, "since": st.since, "detail": st.detail, "mode": None,
                            "uptime_s": None, "last_heartbeat_age_s": None, "last_exit": None, "heartbeats": False}
        files = self._files()
        if st.state == "running" and st.pid is not None:
            mine = [f for f in files if f.pid == st.pid]
            if mine:
                tail = self._events.tail(mine[0])
                head = self._events.head(mine[0])
                start = head if head and head.get("kind") == "scheduler.start" else next((e for e in tail if e.get("kind") == "scheduler.start"), None)
                if start:
                    info["mode"] = start.get("mode")
                    t = parse_time(start.get("ts"))
                    info["uptime_s"] = (now - t).total_seconds() if t else None
                beats = [e for e in tail if e.get("kind") == "scheduler.heartbeat"]
                if beats:
                    t = parse_time(beats[-1].get("ts"))
                    info["heartbeats"] = True
                    info["last_heartbeat_age_s"] = max(0.0, (now - t).total_seconds()) if t else None
                    info["heartbeat_running"] = beats[-1].get("running")
        else:
            for f in files[:3]:
                exits = [e for e in self._events.tail(f) if e.get("kind") == "scheduler.exit"]
                if exits:
                    info["last_exit"] = clip_line(exits[-1].get("reason"), 160)
                    info["last_exit_ts"] = exits[-1].get("ts")
                    break
            if not info["last_exit"]:
                info["last_exit"] = self._marker.read() or None
        return info


class MailInflightBatches(InflightBatches):
    """The agents with a run going (a batch inflight) and the front matter of each message of the batch, one file at a time."""

    def __init__(self, agents: AgentDirectory, mailbox: MailboxReader, files: MailboxFiles, index: MessageIndex) -> None:
        self._agents, self._mailbox, self._files, self._index = agents, mailbox, files, index

    def of_running(self) -> dict[str, list[BatchItem]]:
        batches: dict[str, list[BatchItem]] = {}
        for a in self._agents.agents():
            if not self._mailbox.has_inflight(a):
                continue
            recs = []
            for n in self._files.names(a, "inflight"):
                meta, err, _ = self._index.meta_of(self._files.path(a, "inflight", n))
                if meta:
                    recs.append(BatchItem(str(meta.get("id") or n[:-3]), str(meta.get("title") or ""), str(meta.get("from") or ""),
                                          str(meta["trace"]) if meta.get("trace") else None))
            batches[a] = recs
        return batches


class BatchRunsInFlight(FlightReport):
    """One entry per agent with a run going: the run (from the registry, else the agent's last log), how long it has run, its batch and its traces (the
    recorded one of each message, else the one the history derives)."""

    def __init__(
        self, batches: InflightBatches, registry: RunRegistry, run_logs: RunLogReader, history: MessageHistory, derivers: TraceDerivers
    ) -> None:
        self._batches, self._registry, self._run_logs, self._history, self._derivers = batches, registry, run_logs, history, derivers

    def runs(self, now: datetime) -> list[JsonObject]:
        running_rec = self._registry.all()
        batches = self._batches.of_running()
        derived: list[TraceDeriver] = []  # made when a message has no recorded trace, once

        def trace_of(b: BatchItem) -> str | None:
            if b.trace:
                return b.trace
            if not derived:
                derived.append(self._derivers.derive(self._history.messages()))
            return derived[0].of(b.id)[0]

        runs_now: list[JsonObject] = []
        for a, batch in batches.items():
            rec = running_rec.get(a) or {}
            started = rec.get("started")
            stem = Path(str(rec.get("log", ""))).stem if rec.get("log") else None
            if stem is None:
                logs = [(f.stem, f.path) for f in self._run_logs.files(a)]
                stem = logs[-1][0] if logs else None
            t0 = datetime.fromtimestamp(started, timezone.utc) if isinstance(started, (int, float)) else (stamp_of(stem or "") if stem else None)
            traces = sorted({t for b in batch if (t := trace_of(b))})
            runs_now.append({"agent": a, "run": f"{a}@{stem}" if stem else None, "elapsed_s": (now - t0).total_seconds() if t0 else None,
                             "batch": [b.title or b.id for b in batch], "traces": traces})
        return runs_now


class ReasonedQueue(QueueReport):
    """Every agent with unread mail and the reason it has not started, in the order the checks of the scheduler take."""

    def __init__(self, agents: AgentDirectory, mailbox: MailboxReader, pauses: PauseStore, budgets: BudgetQuery, files: MailboxFiles) -> None:
        self._agents, self._mailbox, self._pauses, self._budgets, self._files = agents, mailbox, pauses, budgets, files

    def queued(self, now: datetime, scheduler_up: bool, running: int, max_parallel: int) -> list[JsonObject]:
        queued: list[JsonObject] = []
        free = max_parallel - running
        for a in self._agents.agents():
            n = self._mailbox.unread(a)
            if not n:
                continue
            paused, budget = self._pauses.paused(a), self._budgets.budget(a) or 0
            if self._mailbox.has_inflight(a):  # mail that arrived during a run waits for the next one (one run per agent at a time)
                reason = "its current run is still going; the next run starts after it"
            elif paused and not (paused == "budget" and budget > 0):
                reason = f"paused: {paused}"
            elif budget <= 0:
                reason = "no budget"
            elif not scheduler_up:
                reason = "scheduler is not running"
            elif free <= 0:
                reason = f"max_parallel ({max_parallel}) runs are busy"
            else:
                reason = "ready: starts on the next tick"
            oldest = min((t for name in self._files.names(a, "inbox") if (t := stamp_of(name))), default=None)
            queued.append({"agent": a, "unread": n, "reason": reason, "waiting_s": (now - oldest).total_seconds() if oldest else None})
        return queued

    def paused(self) -> dict[str, str]:
        return {a: reason for a in self._agents.agents() if (reason := self._pauses.paused(a))}


class LoggedRecentEvents(RecentEvents):
    """The errors of the last fifteen minutes and the time of the last event, from the event files."""

    def __init__(self, events: EventReader) -> None:
        self._events = events

    def errors(self, now: datetime) -> JsonObject:
        errs = [ev for ev in self._events.events(now - ERROR_WINDOW, now) if is_error(ev)]
        return {"count": len(errs), "events": errs[-5:]}

    def last(self, now: datetime) -> datetime | None:
        last_event = None
        for f in self._events.files(now - timedelta(days=2), None)[-3:]:
            for ev in self._events.tail(f, 8192)[-1:]:
                t = parse_time(ev.get("ts"))
                if t and (last_event is None or t > last_event):
                    last_event = t
        return last_event


class MailRootDesk(RootDesk):
    """What waits for root: the lines of the queue of the human, and root's outstanding tasks."""

    def __init__(self, queue: HumanQueue, tasks: TaskQuery) -> None:
        self._queue, self._tasks = queue, tasks

    def waiting(self) -> list[str]:
        return [line for _, line in self._queue.items()]

    def open_tasks(self) -> int:
        return len(self._tasks.outstanding(ROOT))


class FileNowQueries(NowQueries):
    """The view of the moment, from its parts; the time is the clock's unless given."""

    def __init__(
        self, settings: OrgSettings, scheduler: SchedulerReport, flight: FlightReport, queue: QueueReport, events: RecentEvents, desk: RootDesk,
        clock: Clock,
    ) -> None:
        self._settings, self._scheduler, self._flight, self._queue, self._events, self._desk, self._clock = (
            settings, scheduler, flight, queue, events, desk, clock,
        )

    def now_view(self, now: datetime | None = None) -> JsonObject:
        at = aware(now) or self._clock.now()
        max_parallel = int(self._settings.number("max_parallel", int))
        sched = self._scheduler.info(at)
        runs_now = self._flight.runs(at)
        queued = self._queue.queued(at, sched["state"] == "running", len(runs_now), max_parallel)
        last_event = self._events.last(at)
        return {"now": iso(at), "scheduler": sched, "max_parallel": max_parallel, "runs_in_flight": runs_now,
                "queued": queued, "waiting_on_you": self._desk.waiting(), "open_root_tasks": self._desk.open_tasks(),
                "paused": self._queue.paused(), "errors_15m": self._events.errors(at), "last_event": iso(last_event),
                "events_seen": last_event is not None}
