"""Fakes of the queries, and the worlds the contract suites iterate over.

``FixedEventQueries``, ``FixedTraceQueries`` and ``FixedMetricQueries`` are what a consumer (the command line, the MCP tool, the dashboard) is given
when its test is not about what the files say: they answer what they were told to and remember what they were asked.

``disk_world`` and ``memory_world`` are the real queries over event files, messages, run logs and agents on disk and in memory. The world is a
bundle of the three ports and of the means to put a story where they look: an agent, a message (both copies), a run log, an event line. Time is
``stamp(seconds)`` after the origin of the clock, the way ``tests/obs_fixtures.py`` has always written it.
"""

from __future__ import annotations

import itertools
import os
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from ..agents.testing import AgentsHarness, MemoryAgents, fs_agents
from ..attention.testing import ListHumanQueue
from ..budget.testing import FixedBudget
from ..daemon import ExitMarker, SchedulerState
from ..daemon.testing import FakeSchedulerStatus, MemoryExitMarker
from ..eligibility.testing import PauseHarness, fs_pauses, memory_pauses
from ..eventlog.testing import EventLogHarness, fs_event_log, memory_event_log
from ..kernel import ROOT, RUNTIME, STAMP_FORMAT, JsonObject, Message, OrgError, OrgPaths, norm
from ..kernel.testing import T0, FakeClock
from ..mail.testing import MailHarness, MemoryMailbox, fs_mailbox, memory_mailbox
from ..processes import OrphanJudge
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ..settings.testing import SettingsHarness, fs_org_settings, memory_org_settings
from ._checks import (
    BudgetConserved,
    FileIntegrityChecks,
    InflightAccounted,
    JudgedLiveRuns,
    MessagesIntact,
    PidfileSane,
    RunsAccounted,
    SeqGapless,
)
from ._derive import LogTraceDerivers
from ._dispatch import AgentTargetedEvents, ViewDispatcher
from ._events import LogEventQueries
from ._files import FsMailboxFiles, FsSchedulerPidFile
from ._history import IndexedMessageHistory
from ._metrics import DerivedMetricQueries
from ._now import (
    BatchRunsInFlight,
    EventSchedulerReport,
    FileNowQueries,
    LoggedRecentEvents,
    MailInflightBatches,
    MailRootDesk,
    ReasonedQueue,
)
from ._ports import MailboxFiles, SchedulerPidFile
from ._render import TextObservabilityRenderer
from ._runs import RunCollector
from ._trace import DerivedTraceQueries
from .api import EventQueries, IntegrityChecks, MetricQueries, NowQueries, ObservabilityRenderer, ObservabilityText, TraceQueries

__all__ = [
    "FixedEventQueries",
    "FixedOrphanJudge",
    "FixedIntegrityChecks",
    "FixedMetricQueries",
    "FixedNowQueries",
    "FixedObservabilityText",
    "FixedTraceQueries",
    "IMPLEMENTATIONS",
    "ObservabilityWorld",
    "T0",
    "MemoryMailboxFiles",
    "MemorySchedulerPidFile",
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


class FixedNowQueries(NowQueries):
    """The view is exactly ``view``; ``asked`` lists the times it was asked for."""

    def __init__(self, view: JsonObject | None = None) -> None:
        self.view: JsonObject = view if view is not None else {}
        self.asked: list[datetime | None] = []

    def now_view(self, now: datetime | None = None) -> JsonObject:
        self.asked.append(now)
        return dict(self.view)


class FixedIntegrityChecks(IntegrityChecks):
    """The answer is exactly ``result`` (by default every check passes); ``asked`` lists the times it was asked for."""

    def __init__(self, result: JsonObject | None = None) -> None:
        self.result: JsonObject = result if result is not None else {"ok": True, "checks": []}
        self.asked: list[datetime | None] = []

    def check(self, now: datetime | None = None) -> JsonObject:
        self.asked.append(now)
        return dict(self.result)


class FixedObservabilityText(ObservabilityText):
    """The text is exactly ``text`` (a failure to raise, when given, is raised instead); ``asked`` lists the questions."""

    def __init__(self, text: str = "", fails: Exception | None = None) -> None:
        self.text, self.fails = text, fails
        self.asked: list[JsonObject] = []

    def observe_text(
        self, view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None, errors_only: bool = False,
        limit: int = 50, now: datetime | None = None, max_lines: int | None = None,
    ) -> str:
        self.asked.append(dict(view=view, target=target, since=since, by=by, errors_only=errors_only, limit=limit, now=now, max_lines=max_lines))
        if self.fails is not None:
            raise self.fails
        return self.text


class FixedOrphanJudge(OrphanJudge):
    """The verdict on every recorded process is ``verdict`` (``ours``, ``doubt``, ``gone`` or ``foreign``); ``asked`` lists the records."""

    def __init__(self, verdict: str = "gone") -> None:
        self.verdict = verdict
        self.asked: list[dict[str, object]] = []

    def judge(self, record: Mapping[str, object]) -> str:
        self.asked.append(dict(record))
        return self.verdict


class MemoryMailboxFiles(MailboxFiles):
    """The message files of the boxes of an in-memory organization: every file was written at ``written`` (epoch seconds; the same second ``MemoryMailbox``
    gives every message file, long before any ``now`` of a test)."""

    def __init__(self, tree: MemoryAgents, written: float = 1.0) -> None:
        self._tree, self._written = tree, written

    @staticmethod
    def _dir(addr: str, box: str) -> str:
        a = norm(addr)
        return box if a == ROOT else f"{a}/{box}"

    def names(self, addr: str, box: str) -> list[str]:
        d = self._dir(addr, box)
        return [n for n in self._tree.listing(d) or [] if n.endswith(".md") and not n.startswith(".") and f"{d}/{n}" in self._tree.files]

    def path(self, addr: str, box: str, name: str) -> Path:
        return self._tree.root / self._dir(addr, box) / name

    def mtime(self, addr: str, box: str, name: str) -> float | None:
        return self._written if f"{self._dir(addr, box)}/{name}" in self._tree.files else None


class MemorySchedulerPidFile(SchedulerPidFile):
    """There is a pid file when the tree of an in-memory organization has ``.runtime/scheduler.pid``."""

    def __init__(self, tree: MemoryAgents) -> None:
        self._tree = tree

    def exists(self) -> bool:
        return ".runtime/scheduler.pid" in self._tree.files


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
    now: NowQueries
    checks: IntegrityChecks
    renderer: ObservabilityRenderer
    text: ObservabilityText
    scheduler: FakeSchedulerStatus  # ``current`` is the state of the scheduler the views see
    judge: FixedOrphanJudge  # the verdict on every recorded process
    marker: ExitMarker  # why the last scheduler exited by itself
    waiting: ListHumanQueue  # what waits for root's decision: ``entries`` of (message id, line)
    budgets: FixedBudget  # the runs each agent holds: ``held``
    pause: Callable[[str, str], None]  # (addr, reason)
    configure: Callable[[str], None]  # ORG.md becomes this text
    begin_run: Callable[[str], None]  # the inbox of the agent becomes the batch of a run in flight
    pidfile: Callable[[str | None], None]  # the text of ``.runtime/scheduler.pid``; None removes it
    settle: Callable[[], None]  # every message file is old (written long before any ``stamp`` of a test)
    remove: Callable[[str], None]  # the file at this path (relative to the organization) is gone
    put: Callable[[str, str], None]  # a file with this text at this path (relative to the organization)
    read: Callable[[str], str | None]  # the text of the file at this path, None when there is none


def _world(
    mail: MailHarness, runs: RunsHarness, log: EventLogHarness, tree: AgentsHarness, pauses: PauseHarness, settings: SettingsHarness,
    files: MailboxFiles, pid: SchedulerPidFile, remove: Callable[[str], None], settle_files: Callable[[], None],
) -> ObservabilityWorld:
    agents = tree.directory
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

    events = LogEventQueries(log.reader, log.followers, clock)
    traces = DerivedTraceQueries(history, LogTraceDerivers(runs.reader), log.reader, collector, agents, clock)
    metrics = DerivedMetricQueries(log.reader, collector, history, clock)
    layout = OrgPaths(mail.path_of(""))
    scheduler, judge, marker = FakeSchedulerStatus(SchedulerState("stopped")), FixedOrphanJudge("gone"), MemoryExitMarker()
    waiting, budgets = ListHumanQueue(), FixedBudget(mail.tasks, agents, tree.charters)
    live = JudgedLiveRuns(judge)
    batches = MailInflightBatches(agents, mail.reader, files, mail.index)
    queue = ReasonedQueue(agents, mail.reader, pauses.store, budgets, files)
    now = FileNowQueries(
        settings.settings, EventSchedulerReport(scheduler, marker, log.reader), BatchRunsInFlight(batches, runs.registry, runs.reader, history, LogTraceDerivers(runs.reader)),
        queue, LoggedRecentEvents(log.reader), MailRootDesk(waiting, mail.tasks), clock,
    )
    checks = FileIntegrityChecks(
        mail.index,
        [
            MessagesIntact(layout, agents),
            BudgetConserved(agents, budgets, runs.reader, tree.archive),
            InflightAccounted(agents, files, runs.registry, live, scheduler),
            RunsAccounted(log.reader, runs.registry, live, agents, runs.reader),
            SeqGapless(log.reader),
            PidfileSane(pid, scheduler),
        ],
        clock,
    )
    renderer = TextObservabilityRenderer()
    text = ViewDispatcher(AgentTargetedEvents(events, agents, log.reader), traces, metrics, now, checks, renderer)

    def pause(addr: str, reason: str) -> None:
        pauses.agent(addr)
        pauses.store.pause(addr, reason)

    def begin_run(addr: str) -> None:
        mail.batches.begin(addr)

    def pidfile(content: str | None) -> None:
        if content is None:
            remove(".runtime/scheduler.pid")
        else:
            mail.put(".runtime/scheduler.pid", content)

    return ObservabilityWorld(
        events=events, traces=traces, metrics=metrics,
        clock=clock, agent=agent, send=send, run_log=run_log, emit=emit, run_events=run_events, tool=tool, partial_line=partial_line, running=running,
        now=now, checks=checks, renderer=renderer, text=text, scheduler=scheduler, judge=judge, marker=marker, waiting=waiting, budgets=budgets,
        pause=pause, configure=settings.put, begin_run=begin_run, pidfile=pidfile, settle=settle_files, remove=remove, put=mail.put, read=mail.read,
    )


def disk_world(tmp_path: Path) -> ObservabilityWorld:
    """Everything below ``tmp_path`` as the runtime keeps it: event files, message files, run logs, agent directories, ORG.md, pause flags."""
    mail = fs_mailbox(tmp_path)
    layout = OrgPaths(tmp_path)

    def settle() -> None:
        for path in tmp_path.rglob("*.md"):
            if path.parent.name in ("inbox", "inflight", "read", "sent"):
                os.utime(path, (stamp(0).timestamp(), stamp(0).timestamp()))

    def remove(rel: str) -> None:
        (tmp_path / rel).unlink(missing_ok=True)

    world = _world(
        mail, fs_runs(tmp_path), fs_event_log(tmp_path), fs_agents(tmp_path), fs_pauses(tmp_path), fs_org_settings(tmp_path), FsMailboxFiles(layout),
        FsSchedulerPidFile(layout), remove, settle,
    )
    world.configure("---\nmission: test\n---\nrules\n")
    return world


def memory_world(tmp_path: Path) -> ObservabilityWorld:
    """The same organization kept in memory."""
    mail = memory_mailbox(tmp_path)
    tree = cast(MemoryMailbox, mail.reader).agents
    agents = AgentsHarness(tree, tree, tree, tree, tree.put, tree.put_dir, tree.read, tree.listing, {})

    def forget(rel: str) -> None:
        tree.files.pop(rel, None)

    world = _world(
        mail, memory_runs(tmp_path), memory_event_log(tmp_path), agents, memory_pauses(tmp_path), memory_org_settings(tmp_path), MemoryMailboxFiles(tree),
        MemorySchedulerPidFile(tree), forget, lambda: None,
    )
    world.configure("---\nmission: test\n---\nrules\n")
    return world


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    EventQueries: [disk_world, memory_world],
    TraceQueries: [disk_world, memory_world],
    MetricQueries: [disk_world, memory_world],
    NowQueries: [disk_world, memory_world],
    IntegrityChecks: [disk_world, memory_world],
    ObservabilityText: [disk_world, memory_world],
}

PURE = {"ObservabilityRenderer"}  # a pure function of its argument: one implementation, no fake
