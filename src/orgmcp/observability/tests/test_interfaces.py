"""Every class of the package says which interface it implements (rule D), and the package exports exactly its api."""

from __future__ import annotations

import orgmcp.observability as package
from orgmcp.observability import api
from orgmcp.observability._derive import LogTraceDerivers, MessageTraceDeriver
from orgmcp.observability._events import LogEventQueries
from orgmcp.observability._history import IndexedMessageHistory
from orgmcp.observability._metrics import DerivedMetricQueries
from orgmcp.observability._ports import MessageHistory, RunCollection, TraceDeriver, TraceDerivers
from orgmcp.observability._runs import RunCollector
from orgmcp.observability._trace import DerivedTraceQueries
from orgmcp.observability._checks import (
    BudgetConserved,
    FileIntegrityChecks,
    InflightAccounted,
    JudgedLiveRuns,
    MessagesIntact,
    PidfileSane,
    RunsAccounted,
    SeqGapless,
)
from orgmcp.observability._dispatch import VIEWS, AgentTargetedEvents, ViewDispatcher
from orgmcp.observability._now import (
    BatchRunsInFlight,
    EventSchedulerReport,
    FileNowQueries,
    LoggedRecentEvents,
    MailInflightBatches,
    MailRootDesk,
    ReasonedQueue,
)
from orgmcp.observability._ports import (
    FlightReport,
    InflightBatches,
    IntegrityCheck,
    LiveRuns,
    QueueReport,
    RecentEvents,
    RootDesk,
    SchedulerReport,
    TargetedEvents,
)
from orgmcp.observability._render import TextObservabilityRenderer
from orgmcp.observability.api import (
    EventQueries,
    IntegrityChecks,
    MetricQueries,
    NowQueries,
    ObservabilityRenderer,
    ObservabilityText,
    TraceQueries,
)
from orgmcp.observability.testing import (
    FixedEventQueries,
    FixedIntegrityChecks,
    FixedMetricQueries,
    FixedNowQueries,
    FixedObservabilityText,
    FixedTraceQueries,
)


def test_each_class_names_its_interface() -> None:
    assert LogEventQueries.__mro__[1] is EventQueries and FixedEventQueries.__mro__[1] is EventQueries
    assert DerivedTraceQueries.__mro__[1] is TraceQueries and FixedTraceQueries.__mro__[1] is TraceQueries
    assert DerivedMetricQueries.__mro__[1] is MetricQueries and FixedMetricQueries.__mro__[1] is MetricQueries
    assert RunCollector.__mro__[1] is RunCollection and IndexedMessageHistory.__mro__[1] is MessageHistory
    assert MessageTraceDeriver.__mro__[1] is TraceDeriver and LogTraceDerivers.__mro__[1] is TraceDerivers


def test_each_class_of_the_second_half_names_its_interface() -> None:
    assert FileNowQueries.__mro__[1] is NowQueries and FixedNowQueries.__mro__[1] is NowQueries
    assert FileIntegrityChecks.__mro__[1] is IntegrityChecks and FixedIntegrityChecks.__mro__[1] is IntegrityChecks
    assert TextObservabilityRenderer.__mro__[1] is ObservabilityRenderer
    assert ViewDispatcher.__mro__[1] is ObservabilityText and FixedObservabilityText.__mro__[1] is ObservabilityText
    assert EventSchedulerReport.__mro__[1] is SchedulerReport and MailInflightBatches.__mro__[1] is InflightBatches
    assert BatchRunsInFlight.__mro__[1] is FlightReport and ReasonedQueue.__mro__[1] is QueueReport
    assert LoggedRecentEvents.__mro__[1] is RecentEvents and MailRootDesk.__mro__[1] is RootDesk and AgentTargetedEvents.__mro__[1] is TargetedEvents
    assert JudgedLiveRuns.__mro__[1] is LiveRuns
    for check in (MessagesIntact, BudgetConserved, InflightAccounted, RunsAccounted, SeqGapless, PidfileSane):
        assert check.__mro__[1] is IntegrityCheck


def test_the_package_exports_exactly_its_api() -> None:
    assert package.__all__ == api.__all__
    assert set(api.__all__) == {"EventQueries", "TraceQueries", "MetricQueries", "NowQueries", "IntegrityChecks", "ObservabilityRenderer", "ObservabilityText", "percentile", "parse_when", "fmt_rel", "normalize_refusal", "is_error",
                                "format_event"}
    assert all(getattr(package, name) is getattr(api, name) for name in api.__all__)


def test_the_second_half_is_what_its_interfaces_say() -> None:
    from orgmcp.observability._ports import TargetedEvents  # noqa: F401 - the port the dispatcher is given

    assert isinstance(TextObservabilityRenderer(), ObservabilityRenderer)
    assert isinstance(ViewDispatcher.__new__(ViewDispatcher), ObservabilityText)
    assert isinstance(FileNowQueries.__new__(FileNowQueries), NowQueries) and isinstance(FileIntegrityChecks.__new__(FileIntegrityChecks), IntegrityChecks)


def test_the_views_are_those_of_the_tool() -> None:
    assert VIEWS == ("now", "trace", "metrics", "events", "check")
