"""``ComposedQueries``: the five queries of ``dashdata`` and the state they share, asked as one object. Each question goes to the query that answers it, with
its arguments as they were; the event feed is the one the state keeps."""

from __future__ import annotations

import pytest

from orgmcp.dashboard._ports import DashboardQueries
from orgmcp.dashboard._queries import ComposedQueries
from orgmcp.dashboard.testing import SHOWN, health_view, request_row, small_snapshot
from orgmcp.dashdata import (
    AgentDetailQuery,
    HealthQuery,
    MsgRow,
    RequestQuery,
    ServiceQuery,
    SnapshotQuery,
)
from orgmcp.dashdata.testing import (
    FixedAgentDetailQuery,
    FixedEventFeedFactory,
    FixedHealthQuery,
    FixedRequestQuery,
    FixedServiceQuery,
    FixedSnapshotQuery,
    MemoryDashboardState,
    MemoryEventFeed,
)
from orgmcp.kernel.testing import FakeClock

pytestmark = pytest.mark.xfail(strict=True, reason="red: D-dashboard")


class Parts:
    def __init__(self) -> None:
        self.snapshots = FixedSnapshotQuery(small_snapshot())
        self.details = FixedAgentDetailQuery(texts={"m-1": "the text"})
        self.requests = FixedRequestQuery([request_row()], lines={"t-1": "the line"}, traces={"t-1": "the trace"})
        self.services = FixedServiceQuery()
        self.health = FixedHealthQuery(health_view(), (SHOWN, "checked", True))
        self.feed = MemoryEventFeed([{"kind": "run.start"}])
        self.feeds = FixedEventFeedFactory(self.feed)
        self.state = MemoryDashboardState(FakeClock(), self.feeds, lambda: SHOWN)
        self.queries = ComposedQueries(self.snapshots, self.details, self.requests, self.services, self.health, self.state)


def test_it_is_all_five_queries() -> None:
    queries = Parts().queries
    assert isinstance(queries, DashboardQueries)
    for port in (SnapshotQuery, AgentDetailQuery, RequestQuery, ServiceQuery, HealthQuery):
        assert isinstance(queries, port)


def test_the_snapshot_is_the_one_of_the_snapshot_query() -> None:
    parts = Parts()
    assert parts.queries.snapshot() is parts.snapshots.snap
    assert parts.snapshots.asked == 1


def test_the_questions_about_an_agent_go_to_the_detail_query_as_they_were_asked() -> None:
    parts = Parts()
    snap = small_snapshot()
    parts.queries.agent_detail("ops", snap, raw=True)
    parts.queries.run_log("ops", True)
    parts.queries.event_lines([{"kind": "x"}], "ops", True, False)
    row = MsgRow("m-1", "inbox", "note", "root", "ops", "t", None, 0, None, None)
    assert parts.queries.message_text(row) == "the text"
    assert parts.queries.message_lookup("ops", "m-1") is None
    assert parts.details.asked == [
        ("agent_detail", ("ops", True)), ("run_log", ("ops", True)), ("event_lines", (1, "ops", True, False)), ("message_text", ("m-1",)),
        ("message_lookup", ("ops", "m-1")),
    ]


def test_the_requests_services_and_health_go_to_their_queries() -> None:
    parts = Parts()
    queries = parts.queries
    assert [r.id for r in queries.requests()] == ["t-1"]
    assert queries.request_line("t-1") == "the line" and queries.trace_text("t-1") == "the trace"
    assert queries.services() == [] and queries.service_detail("ops", "brief")[0].lines == ["ops/brief: no such service (retired?)"]
    assert queries.health() is parts.health.view and queries.run_check() == (SHOWN, "checked", True)
    assert parts.requests.asked == [("requests", None), ("request_line", "t-1"), ("trace_text", "t-1")]
    assert parts.services.asked == [("services", None), ("service_detail", "ops/brief")]
    assert parts.health.asked == ["health", "run_check"]


def test_the_feed_is_the_one_the_state_keeps() -> None:
    parts = Parts()
    assert parts.queries.feed is None
    parts.state.following(SHOWN)
    assert parts.queries.feed is parts.feed


def test_a_query_can_be_replaced_on_the_object_for_a_test() -> None:
    """The pilot tests of the app make the snapshot fail by assigning ``app.data.snapshot``."""
    parts = Parts()
    parts.queries.snapshot = lambda: (_ for _ in ()).throw(RuntimeError("disk on fire"))  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="disk on fire"):
        parts.queries.snapshot()
