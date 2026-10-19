"""Runtime fields of ``dashdata`` (ARCHITECTURE.md 3.35): one field per port that ``wire_dashdata.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

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

STEP: str | None = "C-dashdata"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "EventFeed": "a value that EventFeedFactory.create returns for each feed (it has its own position in the log), not a port built once",
}


@dataclass(frozen=True)
class Fields:
    snapshot_query: SnapshotQuery
    agent_detail_query: AgentDetailQuery
    request_query: RequestQuery
    service_query: ServiceQuery
    health_query: HealthQuery
    event_feed_factory: EventFeedFactory
    dashboard_state: DashboardState  # what the five queries share; in the runtime of a plain Org it is never asked for
    snapshot_renderer: SnapshotRenderer
