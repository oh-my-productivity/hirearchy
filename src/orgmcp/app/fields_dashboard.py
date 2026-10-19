"""Runtime fields of the ``dashboard`` entry point (ARCHITECTURE.md 6.3): none."""

from __future__ import annotations

from dataclasses import dataclass

STEP: str | None = "D-dashboard"  # set to the step's name when the step fills this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "DashboardLauncher": (
        "the dashboard of one organization is launched by the command line, not asked of a runtime: app.wire_dashboard.dashboard_launcher() makes the launcher "
        "over the queries of the runtime of one dashboard (fields_dashdata: snapshot_query, agent_detail_query, request_query, service_query, health_query, dashboard_state)"
    ),
}


@dataclass(frozen=True)
class Fields:
    """No field: the queries of the dashboard are those of ``fields_dashdata``; ``wire_dashboard.queries_of`` composes them."""
