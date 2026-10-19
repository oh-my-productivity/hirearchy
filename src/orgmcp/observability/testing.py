"""Fakes of the queries, and the worlds the contract suites iterate over.

``FixedEventQueries``, ``FixedTraceQueries`` and ``FixedMetricQueries`` are what a consumer (the command line, the MCP tool, the dashboard) is given
when its test is not about what the files say: they answer what they were told to and remember what they were asked.

``disk_world`` and ``memory_world`` are the real queries over event files, messages, run logs and agents on disk and in memory. The world is a
bundle of the three ports and of the means to put a story where they look: an agent, a message (both copies), a run log, an event line. Time is
``stamp(seconds)`` after the origin of the clock, the way ``tests/obs_fixtures.py`` has always written it.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from ..agents import AgentDirectory
from ..agents.testing import fs_agents
from ..eventlog.testing import EventLogHarness, fs_event_log, memory_event_log
from ..kernel import ROOT, RUNTIME, STAMP_FORMAT, JsonObject, Message, OrgError, norm
from ..kernel.testing import T0, FakeClock
from ..mail.testing import MailHarness, MemoryMailbox, fs_mailbox, memory_mailbox
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ._derive import LogTraceDerivers
from ._events import LogEventQueries
from ._history import IndexedMessageHistory
from ._metrics import DerivedMetricQueries
from ._runs import RunCollector
from ._trace import DerivedTraceQueries
from .api import EventQueries, MetricQueries, TraceQueries

__all__ = [
    "FixedEventQueries",
    "FixedMetricQueries",
    "FixedTraceQueries",
    "IMPLEMENTATIONS",
    "ObservabilityWorld",
    "T0",
    "disk_world",
    "memory_world",
    "stamp",
]


def stamp(offset_s: float) -> datetime:
    """``offset_s`` seconds after the origin of the clock (10:00 on 2026-10-18)."""
    return T0 + timedelta(seconds=offset_s)


# ------------------------------------------------------------------------------ fakes for consumers


class FixedEventQueries(EventQueries):
    """The view is exactly ``view`` (``events``: its events); ``follow`` yields ``to_follow``. What was asked is in ``asked``, one entry per call."""

    def __init__(self, view: JsonObject | None = None, to_follow: Sequence[JsonObject] = ()) -> None:
        self.view: JsonObject = view if view is not None else {"events": [], "total": 0, "shown": 0, "since": None, "until": None}
        self.to_follow = list(to_follow)
        self.asked: list[tuple[str, JsonObject]] = []

    def events_view(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> JsonObject:
        self.asked.append(("events_view", dict(since=since, until=until, agent=agent, kind=kind, trace=trace, errors=errors, limit=limit, now=now)))
        return dict(self.view)

    def events(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> list[JsonObject]:
        self.asked.append(("events", dict(since=since, until=until, agent=agent, kind=kind, trace=trace, errors=errors, limit=limit, now=now)))
        return list(cast("list[JsonObject]", self.view["events"]))

    def follow(
        self, agent: str | None = None, kind: str | None = None, trace: str | None = None, errors: bool = False, poll: float = 0.5,
        max_polls: int | None = None,
    ) -> Iterator[JsonObject]:
        self.asked.append(("follow", dict(agent=agent, kind=kind, trace=trace, errors=errors, poll=poll, max_polls=max_polls)))
        yield from self.to_follow


class FixedTraceQueries(TraceQueries):
    """The trace of a task is the one in ``traces`` (a task it has none of is an ``OrgError``, like an unknown id); ``asked`` lists the ids."""

    def __init__(self, traces: Mapping[str, JsonObject] | None = None) -> None:
        self.traces = dict(traces or {})
        self.asked: list[tuple[str, datetime | None]] = []

    def trace(self, task_id: str, now: datetime | None = None) -> JsonObject:
        self.asked.append((task_id, now))
        if task_id not in self.traces:
            known = ", ".join(self.traces) or "none"
            raise OrgError(f"no message {task_id}. Root's tasks (latest): {known}")
        return dict(self.traces[task_id])


class FixedMetricQueries(MetricQueries):
    """The metrics are exactly ``result``; ``asked`` lists the questions."""

    def __init__(self, result: JsonObject | None = None) -> None:
        self.result: JsonObject = result if result is not None else {}
        self.asked: list[JsonObject] = []

    def metrics(self, since: str | datetime | None = "24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> JsonObject:
        self.asked.append(dict(since=since, by=by, now=now, agent=agent))
        return dict(self.result)


# ------------------------------------------------------------------------------ worlds


@dataclass(frozen=True)
class ObservabilityWorld:
    """The three ports over one organization, the clock they read, and the means to put a story where they look."""

    events: EventQueries
    traces: TraceQueries
    metrics: MetricQueries
    clock: FakeClock
    agent: Callable[[str], None]  # the agent exists, with a charter and a directory for its run logs
    send: Callable[..., Message]  # (sender, to, kind="task", when=10, *, title, budget, status, reply_to, revises, service, trace, wake, box, body): both copies; trace="self" is its own id
    run_log: Callable[..., str]  # (addr, start, footer="", *, end=None): a run log named after its start; returns the stem
    emit: Callable[..., JsonObject]  # (when, kind, *, proc="mcp", pid=4242, **fields): one event line
    run_events: Callable[..., str]  # (addr, stem, start, seconds, batch, traces, *, ok, timed_out, killed, error): run.start + run.end; returns the run id
    tool: Callable[..., JsonObject]  # (when, actor, tool, *, ok=True, ms=5, error=None, run=None, trace=None, args=None): a tool.call event
    partial_line: Callable[[], None]  # a half-written line at the end of an event file, as a live writer leaves one
    running: Callable[[str, str], None]  # (addr, stem): the registry says the agent's run is in flight


def _world(mail: MailHarness, runs: RunsHarness, log: EventLogHarness, agents: AgentDirectory) -> ObservabilityWorld:
    clock = log.clock
    history = IndexedMessageHistory(mail.index)
    collector = RunCollector(runs.reader, runs.registry, agents, mail.reader, log.reader)
    numbers = itertools.count(1)

    def agent(addr: str) -> None:
        mail.agent(addr)
        runs.add_agent(addr)

    def dir_of(addr: str) -> str:
        return "" if norm(addr) == ROOT else f"{norm(addr)}/"

    def send(
        sender: str, to: str, kind: str = "task", when: float = 10, *, title: str = "T", budget: int = 0, status: str | None = None,
        reply_to: str | None = None, revises: str | None = None, service: str | None = None, trace: str | None = None, wake: bool = True,
        box: str = "inbox", body: str = "b",
    ) -> Message:
        n = next(numbers)
        at = stamp(when)
        msg = Message(
            sender=sender, to=to, type=kind, title=title, body=body, status=status, budget=budget, reply_to=reply_to, revises=revises,
            service=service, trace=trace, wake=wake, id=f"{at:{STAMP_FORMAT}}-{sender.replace('/', '.')}-{n:04x}", created=at.isoformat(),
        )
        if trace == "self":  # the first message of a request is its own trace
            msg.trace = msg.id
        if sender != RUNTIME:
            mail.put(f"{dir_of(sender)}sent/{msg.id}.md", msg.to_text())
        mail.put(f"{dir_of(to)}{box}/{msg.id}.md", msg.to_text())
        return msg

    def run_log(addr: str, start: float, footer: str = "", *, end: float | None = None) -> str:
        name = f"{stamp(start):{STAMP_FORMAT}}"
        path = runs.put_log(addr, f"{name}.log", footer)
        runs.set_mtime(path, stamp(start if end is None else end).timestamp())
        return name

    def emit(when: float, kind: str, *, proc: str = "mcp", pid: int = 4242, **fields: object) -> JsonObject:
        return log.log.emit(stamp(when), kind, proc=proc, pid=pid, **fields)

    def run_events(
        addr: str, stem: str, start: float, seconds: float, batch: list[str], traces: list[str], *, ok: bool = True, timed_out: bool = False,
        killed: bool = False, error: str | None = None, pid: int = 7000,
    ) -> str:
        rid = f"{addr}@{stem}"
        emit(start + 0.005, "run.start", proc="scheduler", pid=pid, run=rid, agent=addr, batch=batch, traces=traces, pgid=1, model=None, budget_before=3)
        emit(start + seconds, "run.end", proc="scheduler", pid=pid, run=rid, agent=addr, ok=ok,
             exit_code=0 if ok else (-9 if killed or timed_out else 1), duration_ms=int(seconds * 1000), timed_out=timed_out, killed=killed,
             budget_after=2, error=error)
        return rid

    def tool(
        when: float, actor: str, tool: str, *, ok: bool = True, ms: int = 5, error: str | None = None, run: str | None = None,
        trace: str | None = None, args: JsonObject | None = None, proc: str = "mcp", pid: int = 4242,
    ) -> JsonObject:
        return emit(when, "tool.call", proc=proc, pid=pid, actor=actor, run=run, trace=trace, tool=tool, ok=ok, ms=ms, error=error,
                    error_type=None if ok else "OrgError", args=args or {})

    def partial_line() -> None:
        log.log.raw(f"{stamp(0):%Y-%m-%d}", "mcp", 4242, '{"v": 1, "ts": "2026-10-18T10:0')

    def running(addr: str, stem: str) -> None:
        runs.registry.record(addr, {"pgid": 1, "lstart": "x", "started": stamp(0).timestamp(), "scheduler": 7000, "log": f"{norm(addr)}/runs/{stem}.log"})

    return ObservabilityWorld(
        events=LogEventQueries(log.reader, log.followers, clock),
        traces=DerivedTraceQueries(history, LogTraceDerivers(runs.reader), log.reader, collector, agents, clock),
        metrics=DerivedMetricQueries(log.reader, collector, history, clock),
        clock=clock, agent=agent, send=send, run_log=run_log, emit=emit, run_events=run_events, tool=tool, partial_line=partial_line, running=running,
    )


def disk_world(tmp_path: Path) -> ObservabilityWorld:
    """Everything below ``tmp_path`` as the runtime keeps it: event files, message files, run logs, agent directories."""
    return _world(fs_mailbox(tmp_path), fs_runs(tmp_path), fs_event_log(tmp_path), fs_agents(tmp_path).directory)


def memory_world(tmp_path: Path) -> ObservabilityWorld:
    """The same organization kept in memory."""
    mail = memory_mailbox(tmp_path)
    return _world(mail, memory_runs(tmp_path), memory_event_log(tmp_path), cast(MemoryMailbox, mail.reader).agents)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    EventQueries: [disk_world, memory_world],
    TraceQueries: [disk_world, memory_world],
    MetricQueries: [disk_world, memory_world],
}
