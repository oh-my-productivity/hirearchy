"""Contract of ``HealthReport``: who is flagged, and the JSON-able form of a report. ``OrgHealth`` is its one implementation (data)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from hirearchy.health import FLAGS, AgentHealth, BranchHealth, HealthReport, OrgHealth

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def agent(addr: str, **flags: str) -> AgentHealth:
    return AgentHealth(
        addr=addr, depth=addr.count("/") + 1, state="idle", budget_left=3, budget_received=5, runs_used=2, tasks_received=1, open_tasks=0,
        oldest_open_age=None, done=1, failed=0, blocked=0, runs_per_task=2.0, rework=0, empty_runs=0, last_activity=NOW,
        since_activity=60.0, flags=dict(flags),
    )


def report() -> OrgHealth:
    branch = BranchHealth("root", 2, 4, 0, 2, 0, 0, 0, "stuck")
    return OrgHealth("root", NOW, [agent("ceo", stuck="open task is 1h old"), agent("ops")], {"root": branch})


def test_the_report_is_a_health_report() -> None:
    assert isinstance(report(), HealthReport)


def test_the_flagged_agents_are_the_ones_with_a_flag() -> None:
    assert [a.addr for a in report().flagged] == ["ceo"]
    assert OrgHealth("root", NOW, [agent("ops")], {}).flagged == []


def test_the_dictionary_is_json_with_times_as_iso_text() -> None:
    data = report().to_dict()
    assert json.loads(json.dumps(data)) == data
    assert data["now"] == "2026-01-01T12:00:00+00:00"
    assert data["flagged"] == ["ceo"] and data["root"] == "root"
    agents = data["agents"]
    assert isinstance(agents, list) and agents[0]["last_activity"] == "2026-01-01T12:00:00+00:00"
    assert agents[0]["flags"] == {"stuck": "open task is 1h old"}


def test_a_missing_time_stays_null() -> None:
    quiet = agent("ops")
    quiet.last_activity = None
    data = OrgHealth("root", NOW, [quiet], {}).to_dict()
    assert data["agents"][0]["last_activity"] is None  # type: ignore[index]


def test_the_worst_flag_is_the_first_of_the_ranking() -> None:
    assert FLAGS[0] == "stuck" and FLAGS[-1] == "idle"
    both = agent("ceo", idle="quiet", paused="by hand")
    assert both.worst_flag == "paused" and agent("ops").worst_flag is None
