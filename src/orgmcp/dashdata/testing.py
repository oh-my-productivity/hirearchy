"""Fakes of the queries of the dashboard, and the worlds the contract suites iterate over.

``FixedSnapshotQuery``, ``FixedAgentDetailQuery``, ``FixedRequestQuery``, ``FixedServiceQuery``, ``FixedHealthQuery``, ``MemoryEventFeed`` and
``FixedEventFeedFactory`` are what the dashboard application is given when its test is not about what the files say: they answer what they were told to
and remember what they were asked.

``plain_world`` and ``caching_world`` are the real queries over an organization on disk: with the strict ports of the packages they read, and with the
decorators the dashboard puts in their place (the agent tree and the mailboxes listed per change of the directory, the run counts, the pause flags and
ORG.md cached). Both must give the same answers (the contract suites run over both). The world is a bundle of the queries and of the means to put a story
where they look: an agent, a message, a run log, an event, a service, a case, the health of an agent. Time is ``stamp(seconds)`` after the origin of
the clock, the way ``tests/obs_fixtures.py`` has always written it; what the dashboard shows as "now" is ``world.shown``.

``disk_feed`` and ``memory_feed`` are the event feed over event files and over memory; ``cache_state`` and ``MemoryDashboardState`` are the state the
queries share, real and fake.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeVar, cast

from ..access.testing import static_access
from ..agents.testing import AgentsHarness, caching_agents, fs_agents
from ..daemon import ExitMarker, SchedulerStatus
from ..eligibility.testing import PauseHarness, caching_pauses, fs_pauses
from ..eventlog import EventFollowers, EventReader
from ..eventlog.testing import EventLogHarness, fs_event_log, memory_event_log
from ..health.testing import FixedHealthAnalyzer
from ..kernel import ROOT, JsonObject, Message, OrgError, OrgPaths, aware
from ..kernel.testing import FakeClock
from ..mail.testing import MailHarness, caching_mailbox, fs_mailbox
from ..observability import EventQueries, is_error, parse_when
from ..observability.testing import ObservabilityWorld, disk_world, stamp
from ..progress.testing import FixedProgressReporter
from ..reflection import Case, CaseHistory
from ..runs.testing import RunsHarness, caching_fs_runs, fs_runs
from ..services import Contract, Playbook, ServiceCatalog
from ..settings.testing import SettingsHarness, caching_org_settings, fs_org_settings
from ._cache import DashCache
from ._clock import GivenDashTime
from ._data import (
    AgentDetail,
    AgentRow,
    HealthView,
    MsgRow,
    RequestRow,
    RunLog,
    SchedulerView,
    Section,
    ServiceRow,
    Snapshot,
)
from ._detail import CachedAgentDetailQuery
from ._events import EventLine
from ._feed import FeedBuffer, FeedBufferFactory
from ._health import CachedHealthQuery
from ._lookup import MailWordedEvents
from ._messages import MailMessageViews
from ._overview import MailAgentOverviews
from ._ports import CaseVerdicts, EventFilters, MtimeProbe, RequestFacts, UnreadableSource
from ._probe import DirMtimeProbe
from ._render import TextSnapshotRenderer
from ._requests import CachedRequestQuery, MailRequestRows, ProgressRequestTexts
from ._rows import CharterProfile, LogRunElapsed, MailAgentWork, StateRows
from ._runlog import CachedRunLogViews
from ._scheduler import EventSchedulerViews, FsEventFileStamps
from ._services import CachedServiceQuery
from ._site import FsOrgSite, Problems
from ._snapshot import CachedSnapshotQuery
from ._texts import FileAgentTexts
from .api import (
    FEED_BACKFILL,
    FEED_KEEP,
    AgentDetailQuery,
    DashboardState,
    EventFeed,
    EventFeedFactory,
    HealthQuery,
    RequestQuery,
    ServiceQuery,
    SnapshotQuery,
    SnapshotRenderer,
)

T = TypeVar("T")

# ------------------------------------------------------------------------------ fakes for consumers


class FixedSnapshotQuery(SnapshotQuery):
    """``snapshot`` answers ``snap`` (the same object every time); ``asked`` counts the calls."""

    def __init__(self, snap: Snapshot) -> None:
        self.snap = snap
        self.asked = 0

    def snapshot(self) -> Snapshot:
        self.asked += 1
        return self.snap


class FixedAgentDetailQuery(AgentDetailQuery):
    """``agent_detail`` answers the detail put in for the agent (an agent it has none of is "no such agent"); ``asked`` lists the questions."""

    def __init__(self, details: Mapping[str, AgentDetail] | None = None, logs: Mapping[str, RunLog] | None = None, texts: Mapping[str, str] | None = None) -> None:
        self.details = dict(details or {})
        self.logs = dict(logs or {})
        self.texts = dict(texts or {})
        self.asked: list[tuple[str, tuple[object, ...]]] = []

    def agent_detail(self, addr: str, snap: Snapshot | None = None, raw: bool = False) -> AgentDetail:
        self.asked.append(("agent_detail", (addr, raw)))
        return self.details.get(addr) or AgentDetail(addr, None, [Section("", [f"{addr}: no such agent (any more)"])], [], RunLog(), "", "", [])

    def run_log(self, addr: str, live: bool) -> RunLog:
        self.asked.append(("run_log", (addr, live)))
        return self.logs.get(addr) or RunLog(note="this agent has not run yet")

    def message_text(self, row: MsgRow) -> str:
        self.asked.append(("message_text", (row.id,)))
        return self.texts.get(row.id, "(message file is gone)")

    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        self.asked.append(("message_lookup", (agent, mid)))
        return None

    def event_lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        self.asked.append(("event_lines", (len(events), me, actor, raw)))
        return [EventLine(str(ev.get("kind", "?")), False) for ev in events]


class FixedRequestQuery(RequestQuery):
    """``requests`` answers ``rows``; the line and the trace of a task are the ones put in (else "no trace"); ``asked`` lists the questions."""

    def __init__(self, rows: Sequence[RequestRow] = (), lines: Mapping[str, str] | None = None, traces: Mapping[str, str] | None = None) -> None:
        self.rows = list(rows)
        self.lines = dict(lines or {})
        self.traces = dict(traces or {})
        self.asked: list[tuple[str, str | None]] = []

    def requests(self, snap: Snapshot | None = None) -> list[RequestRow]:
        self.asked.append(("requests", None))
        return list(self.rows)

    def trace_text(self, task_id: str) -> str:
        self.asked.append(("trace_text", task_id))
        return self.traces.get(task_id, f"no trace: no message {task_id}")

    def request_line(self, task_id: str) -> str:
        self.asked.append(("request_line", task_id))
        return self.lines.get(task_id, f"(no progress line: no message {task_id})")


class FixedServiceQuery(ServiceQuery):
    """``services`` answers ``rows``; the detail of a service is the one put in (else "no such service"); ``asked`` lists the questions."""

    def __init__(self, rows: Sequence[ServiceRow] = (), details: Mapping[tuple[str, str], list[Section]] | None = None) -> None:
        self.rows = list(rows)
        self.details = dict(details or {})
        self.asked: list[tuple[str, str | None]] = []

    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        self.asked.append(("services", None))
        return list(self.rows)

    def service_detail(self, owner: str, name: str) -> list[Section]:
        self.asked.append(("service_detail", f"{owner}/{name}"))
        return self.details.get((owner, name)) or [Section("", [f"{owner}/{name}: no such service (retired?)"])]


class FixedHealthQuery(HealthQuery):
    """``health`` answers ``view``; ``run_check`` answers ``checked`` (when, text, all passed); ``asked`` lists the questions."""

    def __init__(self, view: HealthView, checked: tuple[datetime, str, bool]) -> None:
        self.view = view
        self.checked = checked
        self.asked: list[str] = []

    def health(self, snap: Snapshot | None = None) -> HealthView:
        self.asked.append("health")
        return self.view

    def run_check(self) -> tuple[datetime, str, bool]:
        self.asked.append("run_check")
        return self.checked


class MemoryEventFeed(EventFeed):
    """A feed that holds the events it is given (``add``), and is "polled" by moving them in (``arrive``): the log of a test that has no files."""

    def __init__(self, events: Sequence[JsonObject] = ()) -> None:
        self.events: list[JsonObject] = list(events)
        self.any = bool(self.events)
        self.version = 0
        self.last_ts: datetime | None = None
        self.waiting: list[JsonObject] = []
        self.polled: list[datetime | None] = []

    def arrive(self, *events: JsonObject) -> None:
        """These events are appended to the log; the next ``poll`` brings them in."""
        self.waiting.extend(events)

    def poll(self, now: datetime | None = None) -> int:
        self.polled.append(now)
        arrived, self.waiting = self.waiting, []
        self.events.extend(arrived)
        if arrived:
            self.version += 1
            self.any = True
        return len(arrived)

    def error_count(self, now: datetime) -> int:
        return sum(1 for ev in self.events if is_error(ev))

    def matching(self, text: str = "", errors: bool = False, agent: str | None = None, limit: int = 1000) -> list[JsonObject]:
        words = [w.lower() for w in text.split()]
        out = [
            ev for ev in self.events
            if (not errors or is_error(ev)) and (agent is None or agent in (ev.get("actor"), ev.get("agent"), ev.get("from"), ev.get("to")))
            and all(w in " ".join(str(v) for v in ev.values()).lower() for w in words)
        ]
        return out[-limit:]


class FixedEventFeedFactory(EventFeedFactory):
    """``create`` hands out the feed it was given (the same one every time) and remembers how it was asked."""

    def __init__(self, feed: EventFeed) -> None:
        self.feed = feed
        self.asked: list[tuple[int, str, datetime | None]] = []

    def create(self, keep: int = FEED_KEEP, backfill: str = FEED_BACKFILL, now: datetime | None = None) -> EventFeed:
        self.asked.append((keep, backfill, now))
        return self.feed


class MemoryDashboardState(DashboardState):
    """The state of a dashboard without a cache of directory times: ``mtimes`` is what the directories "have" (-1: missing)."""

    def __init__(self, clock: FakeClock, feeds: EventFeedFactory, now: Callable[[], datetime], mtimes: Mapping[tuple[str, str], int] | None = None) -> None:
        self._clock = clock
        self._now = now
        self._feeds = feeds
        self.mtimes = dict(mtimes or {})
        self.refreshes = 0
        self._memo: dict[str, tuple[tuple[object, ...], float, object]] = {}
        self.feed: EventFeed | None = None
        self.snap: Snapshot | None = None
        self.check_result: tuple[datetime, str, bool] | None = None

    def now(self) -> datetime:
        return self._now()

    def refresh(self) -> None:
        self.refreshes += 1

    def mtime(self, addr: str, name: str) -> int:
        return self.mtimes.get((addr, name), -1)

    def memoised(self, name: str, sig: tuple[object, ...], ttl: float, fn: Callable[[], T]) -> T:
        hit = self._memo.get(name)
        if hit is not None and hit[0] == sig and self._clock.monotonic() - hit[1] < ttl:
            return cast(T, hit[2])
        value = fn()
        self._memo[name] = (sig, self._clock.monotonic(), value)
        return value

    def following(self, now: datetime) -> EventFeed:
        if self.feed is None:
            self.feed = self._feeds.create(now=now)
        else:
            self.feed.poll(now)
        return self.feed


# ------------------------------------------------------------------------------ doubles for the roles of the package


class ScriptedRequestFacts(RequestFacts):
    """What ``progress`` would say of a task, as the test scripts it: ``states`` / ``runs`` by task id (a task it knows nothing of is "working", "running: ceo",
    "runs 0 of 0"), ``activity`` (when the team last did anything), ``delivered`` (artifacts of a result, by the id of the result)."""

    def __init__(self) -> None:
        self.states: dict[str, tuple[str, str]] = {}
        self.runs: dict[str, str] = {}
        self.activity: datetime | None = None
        self.delivered: dict[str, list[str]] = {}
        self.broken: set[str] = set()  # tasks whose state cannot be computed

    def state_of(self, task: Message, result: Message | None, team: Sequence[str]) -> tuple[str, str]:
        if task.id in self.broken:
            raise OrgError("cannot tell")
        return self.states.get(task.id, ("working", "running: ceo"))

    def runs_text(self, task: Message, result: Message | None, team: Sequence[str]) -> str:
        return self.runs.get(task.id, "runs 0 of 0")

    def last_activity(self, team: Sequence[str]) -> datetime | None:
        return self.activity

    def artifacts(self, result: Message) -> list[str]:
        return self.delivered.get(result.id, [])


class PlainEventFilters(EventFilters):
    """The filter of the feed: ``agent`` is the actor, the agent or an end of the message; ``errors`` only what ``is_error`` says."""

    def build(self, agent: str | None, errors: bool) -> Callable[[JsonObject], bool]:
        def match(ev: JsonObject) -> bool:
            if agent and agent not in (ev.get("actor"), ev.get("agent"), ev.get("from"), ev.get("to")):
                return False
            return not errors or is_error(ev)

        return match


class JoinedVerdicts(CaseVerdicts):
    def chain(self, case: Case) -> str:
        return " -> ".join(v.verdict for v in case.verdicts)


class ReaderEventQueries(EventQueries):
    """``events_view`` over an event reader: the window (``since`` / ``until``, durations before ``now``), ``errors`` and ``limit``; nothing else."""

    def __init__(self, reader: EventReader, clock: FakeClock) -> None:
        self._reader = reader
        self._clock = clock

    def events_view(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> JsonObject:
        at = aware(now) or self._clock.now()
        window = (parse_when(since, at) if since else None, parse_when(until, at) if until else None)
        found = [ev for _, ev in self._reader.timed(*window) if not errors or is_error(ev)]
        shown = found[-limit:] if limit else found
        return {"events": shown, "total": len(found), "shown": len(shown), "since": since, "until": until}

    def events(
        self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
        trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None,
    ) -> list[JsonObject]:
        return cast("list[JsonObject]", self.events_view(since, until, agent, kind, trace, errors, limit, now)["events"])

    def follow(
        self, agent: str | None = None, kind: str | None = None, trace: str | None = None, errors: bool = False, poll: float = 0.5,
        max_polls: int | None = None,
    ) -> Iterator[JsonObject]:
        return iter(())


class ListCaseHistory(CaseHistory):
    """The cases are the ones in ``all`` (a test appends to it): ``cases`` answers for the owner and service of each, ``case_of`` finds the case that holds the task."""

    def __init__(self) -> None:
        self.all: list[Case] = []

    def cases(self, owner: str, service: str) -> list[Case]:
        return [c for c in self.all if c.owner == owner and c.service == service]

    def case_of(self, task: Message) -> Case | None:
        return next((c for c in self.all if task.id in {t.id for t in c.tasks}), None)

    def playbook_timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        return []


class ListServiceCatalog(ServiceCatalog):
    """The services are the ones ``define`` put in; the commands of the real catalog are not its business."""

    def __init__(self) -> None:
        self.contracts: dict[tuple[str, str], Contract] = {}
        self.playbooks: dict[tuple[str, str], Playbook] = {}
        self.unreadable: set[tuple[str, str]] = set()

    def define(self, owner: str, name: str, playbook: Playbook | None = None, **fields: object) -> Contract:
        contract = Contract(name=name, owner=owner, **fields)  # type: ignore[arg-type]
        self.contracts[(owner, name)] = contract
        self.playbooks[(owner, name)] = playbook or Playbook()
        return contract

    def service_names(self, addr: str) -> list[str]:
        return sorted(name for owner, name in self.contracts if owner == addr)

    def read_contract(self, owner: str, name: str) -> Contract | None:
        if (owner, name) in self.unreadable:
            raise OrgError(f"{owner}/{name}: SERVICE.md cannot be read")
        return self.contracts.get((owner, name))

    def read_playbook(self, owner: str, name: str) -> Playbook:
        return self.playbooks.get((owner, name), Playbook())

    def owned_services(self, owner: str) -> list[Contract]:
        return [c for (o, _), c in sorted(self.contracts.items()) if o == owner]

    def requestable_services(self, actor: str) -> list[Contract]:
        return [c for (o, _), c in sorted(self.contracts.items()) if o.rpartition("/")[0] == ("" if actor == ROOT else actor)]


# ------------------------------------------------------------------------------ the worlds


@dataclass
class ShownTime:
    """What the dashboard of a world shows as the time (move it with ``at``)."""

    now: datetime = stamp(200)

    def __call__(self) -> datetime:
        return self.now


@dataclass(frozen=True)
class DashWorld:
    """The queries over one organization on disk, and the means to put a story where they look. Addresses of agents: ``ceo``, ``ceo/eng`` ...; root exists."""

    snapshots: SnapshotQuery
    details: AgentDetailQuery
    requests: RequestQuery
    services: ServiceQuery
    health: HealthQuery
    renderer: SnapshotRenderer
    state: DashboardState
    obs: ObservabilityWorld  # the means to author the story: ``agent send run_log emit tool run_events running pause configure begin_run``, and what it sees
    clock: FakeClock  # the clock of the dashboard: it moves the life of a memoised answer
    shown: ShownTime  # the time the dashboard shows
    facts: ScriptedRequestFacts
    catalog: ListServiceCatalog
    history: ListCaseHistory
    analyzer: FixedHealthAnalyzer
    reporter: FixedProgressReporter
    root: Path
    probe: MtimeProbe


def _world(
    tmp_path: Path, agents: AgentsHarness, mail: MailHarness, pauses: PauseHarness, runs: RunsHarness, settings: SettingsHarness, log: EventLogHarness,
) -> DashWorld:
    obs = disk_world(tmp_path)  # the story is told through this one; it writes the files the ports below read
    layout = OrgPaths(tmp_path)
    clock, shown = FakeClock(), ShownTime()
    probe = DirMtimeProbe(layout)
    dash = GivenDashTime(shown, clock)
    facts, catalog, history = ScriptedRequestFacts(), ListServiceCatalog(), ListCaseHistory()
    analyzer = FixedHealthAnalyzer(agents.directory, clock)
    reporter = FixedProgressReporter("progress line")
    events = MailWordedEvents(mail.reader)
    assert mail.parser is not None
    factory = FeedBufferFactory(log.followers, log.reader, obs.events, PlainEventFilters(), clock)
    state = DashCache(dash, probe, factory)
    scheduler = EventSchedulerViews(obs.scheduler, log.reader, FsEventFileStamps(), obs.marker, state, dash, 3.0)
    work = MailAgentWork(mail.reader, mail.tasks)
    rows = StateRows(
        CharterProfile(agents.charters, static_access(tmp_path).models), work, pauses.store, obs.budgets, runs.reader, catalog,
        LogRunElapsed(runs.registry, runs.reader),
    )
    unreadable = [mail.reader] if isinstance(mail.reader, UnreadableSource) else []  # the caching mailbox lists what it skipped
    site = FsOrgSite(layout, state, [Problems(agents.problems), *unreadable])
    snapshots = CachedSnapshotQuery(state, scheduler, agents.directory, settings.settings, rows, obs.waiting, site)
    request_rows = MailRequestRows(mail.reader, agents.directory, facts)
    request_query = CachedRequestQuery(state, snapshots, request_rows, ProgressRequestTexts(reporter, obs.traces, obs.renderer))
    overviews = MailAgentOverviews(agents.charters, work, mail.reader, events, request_query)
    details = CachedAgentDetailQuery(
        state, snapshots, overviews, MailMessageViews(mail.reader, mail.parser), FileAgentTexts(layout),
        CachedRunLogViews(layout, runs.registry, runs.reader), events,
    )
    services = CachedServiceQuery(state, snapshots, agents.directory, catalog, history, JoinedVerdicts())
    health = CachedHealthQuery(state, snapshots, obs.now, obs.renderer, analyzer, obs.checks, events)
    return DashWorld(
        snapshots=snapshots, details=details, requests=request_query, services=services, health=health,
        renderer=TextSnapshotRenderer(snapshots, request_query, services), state=state, obs=obs, clock=clock, shown=shown, facts=facts, catalog=catalog,
        history=history, analyzer=analyzer, reporter=reporter, root=tmp_path, probe=probe,
    )


def plain_world(tmp_path: Path) -> DashWorld:
    """The queries over the strict ports."""
    return _world(tmp_path, fs_agents(tmp_path), fs_mailbox(tmp_path), fs_pauses(tmp_path), fs_runs(tmp_path), fs_org_settings(tmp_path), fs_event_log(tmp_path))


def caching_world(tmp_path: Path) -> DashWorld:
    """The queries over the decorators the dashboard puts in the place of the strict ports."""
    return _world(
        tmp_path, caching_agents(tmp_path), caching_mailbox(tmp_path), caching_pauses(tmp_path), caching_fs_runs(tmp_path), caching_org_settings(tmp_path),
        fs_event_log(tmp_path),
    )


# ------------------------------------------------------------------------------ the feed and the state


@dataclass(frozen=True)
class FeedWorld:
    """The factory of feeds over an event log, and the means to write the log."""

    feeds: EventFeedFactory
    feed: EventFeed
    log: EventLogHarness
    emit: Callable[..., JsonObject]  # (when, kind, **fields): one event line (proc "mcp", pid 4242 unless said otherwise)
    reader: EventReader
    followers: EventFollowers


def _feed_world(log: EventLogHarness) -> FeedWorld:
    factory = FeedBufferFactory(log.followers, log.reader, ReaderEventQueries(log.reader, log.clock), PlainEventFilters(), log.clock)

    def emit(when: float, kind: str, *, proc: str = "mcp", pid: int = 4242, **fields: object) -> JsonObject:
        return log.log.emit(stamp(when), kind, proc=proc, pid=pid, **fields)

    log.clock.t = stamp(200)
    return FeedWorld(factory, factory.create(now=stamp(200)), log, emit, log.reader, log.followers)


def disk_feed(tmp_path: Path) -> FeedWorld:
    return _feed_world(fs_event_log(tmp_path))


def memory_feed(tmp_path: Path) -> FeedWorld:
    return _feed_world(memory_event_log(tmp_path))


def disk_feed_factory(tmp_path: Path) -> FeedWorld:
    """The same world; the factory is what is asked for (``feed`` is one that was made before any event was written)."""
    return disk_feed(tmp_path)


def memory_feed_factory(tmp_path: Path) -> FeedWorld:
    return memory_feed(tmp_path)


@dataclass(frozen=True)
class StateWorld:
    state: DashboardState
    clock: FakeClock
    feeds: FixedEventFeedFactory
    touch: Callable[[str, str, int], None]  # (addr, name, mtime_ns): the directory is stamped
    refreshed: Callable[[], int]  # how often a refresh began


class _CountingProbe(MtimeProbe):
    def __init__(self) -> None:
        self.mtimes: dict[tuple[str, str], int] = {}
        self.ticks = 0

    def tick(self) -> None:
        self.ticks += 1

    def mtime(self, addr: str, name: str) -> int:
        return self.mtimes.get((addr, name), -1)


def cache_state(tmp_path: Path) -> StateWorld:
    clock, feeds, probe = FakeClock(), FixedEventFeedFactory(MemoryEventFeed()), _CountingProbe()
    state = DashCache(GivenDashTime(lambda: stamp(200), clock), probe, feeds)

    def touch(addr: str, name: str, mtime: int) -> None:
        probe.mtimes[(addr, name)] = mtime

    return StateWorld(state, clock, feeds, touch, lambda: probe.ticks)


def memory_state(tmp_path: Path) -> StateWorld:
    clock, feeds = FakeClock(), FixedEventFeedFactory(MemoryEventFeed())
    state = MemoryDashboardState(clock, feeds, lambda: stamp(200))

    def touch(addr: str, name: str, mtime: int) -> None:
        state.mtimes[(addr, name)] = mtime

    return StateWorld(state, clock, feeds, touch, lambda: state.refreshes)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    SnapshotQuery: [plain_world, caching_world],
    AgentDetailQuery: [plain_world, caching_world],
    RequestQuery: [plain_world, caching_world],
    ServiceQuery: [plain_world, caching_world],
    HealthQuery: [plain_world, caching_world],
    SnapshotRenderer: [plain_world, caching_world],
    EventFeed: [disk_feed, memory_feed],
    EventFeedFactory: [disk_feed_factory, memory_feed_factory],
    DashboardState: [cache_state, memory_state],
}

__all__ = [
    "DashWorld", "FeedWorld", "FixedAgentDetailQuery", "FixedEventFeedFactory", "FixedHealthQuery", "FixedRequestQuery", "FixedServiceQuery",
    "FixedSnapshotQuery", "IMPLEMENTATIONS", "JoinedVerdicts", "ListCaseHistory", "ListServiceCatalog", "MemoryDashboardState", "MemoryEventFeed",
    "PlainEventFilters", "ReaderEventQueries", "ScriptedRequestFacts", "ShownTime", "StateWorld", "cache_state", "caching_world", "disk_feed",
    "disk_feed_factory", "memory_feed", "memory_feed_factory", "memory_state", "plain_world",
]
