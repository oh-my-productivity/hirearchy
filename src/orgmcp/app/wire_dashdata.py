"""Providers of the ``dashdata`` ports (ARCHITECTURE.md 6.1), and the runtime of one dashboard.

The queries are made of small roles (the rows of the tree, the scheduler as the event files tell it, the overviews, the messages, the run logs, the
requests, the services, the health, the wording of events) that are private to the package and made here, inside the provider of the port that
uses them. The five queries share ONE ``DashboardState`` (the cache of the dashboard), so a runtime has one of each.

``dashboard_runtime`` is the runtime of ``orgmcp dash``: the ports of a plain ``open_runtime`` with the read ports the dashboard can afford to be
lenient with put in place of the strict ones (``open_runtime`` overrides, so everything derived from them - budgets, what may run, the health of
the agents, the views of ``observability``, the report of ``progress``, the cases of ``reflection`` - is derived from the lenient ones):

* the agent tree is listed per change of the directory and a charter that does not parse is skipped (``agents``);
* the mailboxes are read per change of their directory, and a message that does not parse is skipped (``mail``);
* ORG.md is parsed once per change and a damaged one means the defaults (``settings``);
* the run counts are listed per change of ``runs/`` (``runs``) and the pause flags read per change of their file (``eligibility``).

They are told about changes by one ``DirMtimeProbe`` (a ``stat`` per directory per refresh), and report what they skipped to the dashboard.
Nothing writes anything: the dashboard is read-only (``app/tests/test_wire_dashdata.py`` runs every query over a writer that raises).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from ..access import ModelResolver
from ..agents import AgentDirectory, CharterReader
from ..agents._caching import CachingAgentDirectory, FsCharterStamps, LenientCharterReader
from ..attention import HumanQueue
from ..budget import BudgetQuery
from ..daemon import ExitMarker, SchedulerStatus
from ..dashdata import (
    AgentDetailQuery,
    DashboardState,
    EventFeedFactory,
    HealthQuery,
    RequestQuery,
    ServiceQuery,
    SnapshotQuery,
    SnapshotRenderer,
)
from ..dashdata._cache import DashCache
from ..dashdata._clock import ClockDashTime, DashSettings, GivenDashTime
from ..dashdata._detail import CachedAgentDetailQuery
from ..dashdata._feed import FeedBufferFactory
from ..dashdata._health import CachedHealthQuery
from ..dashdata._lookup import MailWordedEvents
from ..dashdata._messages import MailMessageViews
from ..dashdata._overview import MailAgentOverviews
from ..dashdata._ports import (
    CaseVerdicts,
    DashClock,
    EventFilters,
    MtimeProbe,
    ReadableEvents,
    RequestFacts,
)
from ..dashdata._probe import DirMtimeProbe
from ..dashdata._render import TextSnapshotRenderer
from ..dashdata._requests import CachedRequestQuery, MailRequestRows, ProgressRequestTexts
from ..dashdata._rows import CharterProfile, LogRunElapsed, MailAgentWork, StateRows
from ..dashdata._runlog import CachedRunLogViews
from ..dashdata._runlog import read_tail as read_tail  # re-exported for dashboard_data.py
from ..dashdata._scheduler import EventSchedulerViews, FsEventFileStamps
from ..dashdata._services import CachedServiceQuery
from ..dashdata._texts import FileAgentTexts
from ..dashdata._site import FsOrgSite, Problems, Unreadable
from ..dashdata._snapshot import CachedSnapshotQuery
from ..eligibility import PauseStore
from ..eligibility._caching import CachingPauseStore
from ..eventlog import EventFollowers, EventReader
from ..kernel import Clock, JsonObject, Message, OrgLayout
from ..mail import MailboxReader, MessageParser, TaskQuery
from ..mail._caching import DirMtimeCachingMailbox
from ..observability import EventQueries, IntegrityChecks, NowQueries, ObservabilityRenderer, TraceQueries
from ..progress import ProgressReporter
from ..progress._activity import FsTeamActivity
from ..progress._counts import LogRunCounts
from ..progress._lines import artifacts_of
from ..progress._states import MailTaskStates
from ..reflection import Case, CaseHistory
from ..reflection._digest import verdict_chain
from ..runs import RunLogReader, RunRegistry
from ..runs._caching import CachingRunLogReader
from ..services import ServiceCatalog
from ..settings import OrgSettings
from ..settings._caching import CachingOrgSettings
from ..settings._stamp import FsOrgDocumentStamp
from ..health import HealthAnalyzer
from . import wiring
from ._builder import Builder
from ._lazy import PortResolver
from .runtime import OrgRuntime
from .wire_observability import matcher


class ObservabilityEventFilters(EventFilters):
    """The filter of ``observability`` (the one ``events --agent --errors`` uses) for the events the feed keeps."""

    def build(self, agent: str | None, errors: bool) -> Callable[[JsonObject], bool]:
        return matcher(agent=agent, errors=errors)


class ReflectionVerdicts(CaseVerdicts):
    def chain(self, case: Case) -> str:
        return verdict_chain(case)


class ProgressRequestFacts(RequestFacts):
    """The pieces of a task line that ``progress`` computes: its state, its runs, when the team last did anything, what it delivered."""

    def __init__(self, states: MailTaskStates, counts: LogRunCounts, activity: FsTeamActivity) -> None:
        self._states = states
        self._counts = counts
        self._activity = activity

    def state_of(self, task: Message, result: Message | None, team: Sequence[str]) -> tuple[str, str]:
        state, who = self._states.state_of(task, result, team)
        return state, who

    def runs_text(self, task: Message, result: Message | None, team: Sequence[str]) -> str:
        return self._counts.runs_text(task, result, team)

    def last_activity(self, team: Sequence[str]) -> datetime | None:
        return self._activity.newest(team)

    def artifacts(self, result: Message) -> list[str]:
        return artifacts_of(result)


def request_facts(b: PortResolver) -> RequestFacts:
    mail = b.get(MailboxReader)
    return ProgressRequestFacts(
        MailTaskStates(mail, b.get(PauseStore), b.get(TaskQuery)), LogRunCounts(mail, b.get(RunLogReader)), FsTeamActivity(b.get(OrgLayout)),
    )


def event_feeds(b: PortResolver) -> EventFeedFactory:
    return FeedBufferFactory(b.get(EventFollowers), b.get(EventReader), b.get(EventQueries), b.get(EventFilters), b.get(Clock))


def dashboard_state(b: PortResolver) -> DashboardState:
    return DashCache(b.get(DashClock), b.get(MtimeProbe), b.get(EventFeedFactory))


def snapshot_query(b: PortResolver) -> SnapshotQuery:
    state, clock = b.get(DashboardState), b.get(DashClock)
    scheduler = EventSchedulerViews(
        b.get(SchedulerStatus), b.get(EventReader), FsEventFileStamps(), b.get(ExitMarker), state, clock, b.get(DashSettings).scheduler_ttl,
    )
    mail, tasks = b.get(MailboxReader), b.get(TaskQuery)
    work = MailAgentWork(mail, tasks)
    elapsed = LogRunElapsed(b.get(RunRegistry), b.get(RunLogReader))
    rows = StateRows(
        CharterProfile(b.get(CharterReader), b.get(ModelResolver)), work, b.get(PauseStore), b.get(BudgetQuery), b.get(RunLogReader),
        b.get(ServiceCatalog), elapsed,
    )
    site = FsOrgSite(b.get(OrgLayout), state, b.get(Unreadable).sources)
    return CachedSnapshotQuery(state, scheduler, b.get(AgentDirectory), b.get(OrgSettings), rows, b.get(HumanQueue), site)


def agent_detail_query(b: PortResolver) -> AgentDetailQuery:
    mail, layout = b.get(MailboxReader), b.get(OrgLayout)
    events = b.get(ReadableEvents)
    overviews = MailAgentOverviews(b.get(CharterReader), MailAgentWork(mail, b.get(TaskQuery)), mail, events, b.get(RequestQuery))
    return CachedAgentDetailQuery(
        b.get(DashboardState), b.get(SnapshotQuery), overviews, MailMessageViews(mail, b.get(MessageParser)), FileAgentTexts(layout),
        CachedRunLogViews(layout, b.get(RunRegistry), b.get(RunLogReader)), events,
    )


def request_query(b: PortResolver) -> RequestQuery:
    rows = MailRequestRows(b.get(MailboxReader), b.get(AgentDirectory), b.get(RequestFacts))
    texts = ProgressRequestTexts(b.get(ProgressReporter), b.get(TraceQueries), b.get(ObservabilityRenderer))
    return CachedRequestQuery(b.get(DashboardState), b.get(SnapshotQuery), rows, texts)


def service_query(b: PortResolver) -> ServiceQuery:
    return CachedServiceQuery(
        b.get(DashboardState), b.get(SnapshotQuery), b.get(AgentDirectory), b.get(ServiceCatalog), b.get(CaseHistory), b.get(CaseVerdicts),
    )


def health_query(b: PortResolver) -> HealthQuery:
    return CachedHealthQuery(
        b.get(DashboardState), b.get(SnapshotQuery), b.get(NowQueries), b.get(ObservabilityRenderer), b.get(HealthAnalyzer),
        b.get(IntegrityChecks), b.get(ReadableEvents),
    )


def snapshot_renderer(b: PortResolver) -> SnapshotRenderer:
    return TextSnapshotRenderer(b.get(SnapshotQuery), b.get(RequestQuery), b.get(ServiceQuery))


def renderer_over(snapshots: SnapshotQuery, requests: RequestQuery, services: ServiceQuery) -> SnapshotRenderer:
    """The text of ``dash --once`` over these queries (``dashboard_data.render_once(data)``, which is given one object that is all three)."""
    return TextSnapshotRenderer(snapshots, requests, services)


def register(b: Builder) -> None:
    b.provide(MtimeProbe, lambda b: DirMtimeProbe(b.get(OrgLayout)))
    b.provide(DashClock, lambda b: ClockDashTime(b.get(Clock)))
    b.provide(DashSettings, lambda b: DashSettings())
    b.provide(Unreadable, lambda b: Unreadable())
    b.provide(EventFilters, lambda b: ObservabilityEventFilters())
    b.provide(CaseVerdicts, lambda b: ReflectionVerdicts())
    b.provide(RequestFacts, request_facts)
    b.provide(ReadableEvents, lambda b: MailWordedEvents(b.get(MailboxReader)))
    b.provide(EventFeedFactory, event_feeds)
    b.provide(DashboardState, dashboard_state)
    b.provide(SnapshotQuery, snapshot_query)
    b.provide(AgentDetailQuery, agent_detail_query)
    b.provide(RequestQuery, request_query)
    b.provide(ServiceQuery, service_query)
    b.provide(HealthQuery, health_query)
    b.provide(SnapshotRenderer, snapshot_renderer)


# ------------------------------------------------------------------------------ the runtime of one dashboard


def dashboard_runtime(
    root: Path, now: Callable[[], datetime] | None = None, scheduler_ttl: float = 3.0, overrides: Mapping[type, object] | None = None,
) -> OrgRuntime:
    """The runtime of ``orgmcp dash`` over the organization at ``root`` (resolved by the caller): see the module docstring.

    ``now``: the time the dashboard shows (default: the clock's); ``scheduler_ttl``: how long the state of the scheduler is trusted; ``overrides``:
    ports put in the place of the plain ones, as ``open_runtime`` takes them (a test says the scheduler, a writer that raises ...)."""
    plain = wiring.open_runtime(root, overrides)
    probe = DirMtimeProbe(plain.paths)
    problems: dict[str, str] = {}
    mailbox = DirMtimeCachingMailbox(plain.mailbox, plain.paths, plain.message_parser, probe, plain.clock)
    lenient: dict[type, object] = {
        MtimeProbe: probe,
        Unreadable: Unreadable((Problems(problems), mailbox)),
        AgentDirectory: CachingAgentDirectory(plain.agents, probe, plain.clock),
        CharterReader: LenientCharterReader(plain.charters, FsCharterStamps(plain.paths), problems),
        MailboxReader: mailbox,
        OrgSettings: CachingOrgSettings(plain.settings, FsOrgDocumentStamp(plain.paths), problems),
        RunLogReader: CachingRunLogReader(plain.run_log_reader, probe, plain.clock),
        PauseStore: CachingPauseStore(plain.pause_store, probe),
        DashSettings: DashSettings(scheduler_ttl),
    }
    if now is not None:
        lenient[DashClock] = GivenDashTime(now, plain.clock)
    return wiring.open_runtime(root, {**(overrides or {}), **lenient})
