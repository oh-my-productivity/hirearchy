"""Contract of ``HealthQuery``: what is happening now, the agents the health analysis flags, and the integrity checks on demand. Over the strict ports and over the dashboard's."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashdata import HealthQuery
from orgmcp.dashdata.testing import IMPLEMENTATIONS, DashWorld
from orgmcp.health import AgentHealth

from ._support import make_world, stamp, team


@pytest.fixture(params=IMPLEMENTATIONS[HealthQuery], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DashWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.health, HealthQuery)
    return made


def healthy(addr: str, **flags: str) -> AgentHealth:
    return AgentHealth(addr, addr.count("/") + 1, "idle", 3, 3, 0, 0, 0, None, 0, 0, 0, None, 0, 0, None, None, dict(flags))


def agents_known(w: DashWorld) -> None:
    team(w)
    for addr in ("ceo", "ceo/analyst", "ceo/writer", "ops"):
        w.analyzer.put(healthy(addr))


def test_the_health_view_has_what_is_happening_now(w: DashWorld) -> None:
    agents_known(w)
    view = w.health.health()
    assert view.at == stamp(200) and view.summary == "4 agent(s), 0 flagged" and view.flagged == []
    assert view.now_text.startswith("scheduler: stopped") and "waiting on you: nothing" in view.now_text


def test_the_flagged_agents_come_with_their_reasons(w: DashWorld) -> None:
    agents_known(w)
    w.analyzer.put(healthy("ops", stuck="open task for 40m", paused="paused: x"))
    view = w.health.health()
    assert view.summary == "4 agent(s), 1 flagged" and view.flagged == [("ops", [("stuck", "open task for 40m"), ("paused", "paused: x")])]


def test_a_failing_analysis_is_a_summary_not_an_error(w: DashWorld) -> None:
    team(w)  # the analyzer has been told nothing about these agents
    view = w.health.health()
    assert view.summary.startswith("health failed: OrgError: no health was put in for ceo") and view.flagged == [] and view.now_text


def test_agents_that_wait_for_a_pause_or_a_budget_are_listed_apart_from_the_queue(w: DashWorld) -> None:
    agents_known(w)
    w.obs.pause("ops", "broken")
    w.obs.send("root", "ops", "note", 10, title="Hello")
    w.obs.send("root", "ceo", "note", 11, title="Hello")
    text = w.health.health().now_text
    queued = text.split("queued, not running")[1].split("not started")[0]
    assert "ceo" in queued and "ops" not in queued
    assert "not started, with unread mail (1):\n  ops: 1 unread, oldest 3m10s - paused: broken" in text


def test_the_recent_errors_are_readable_lines(w: DashWorld) -> None:
    agents_known(w)
    w.obs.tool(150, "ceo", "delegate", ok=False, error="not enough budget", args={"to": "ceo/analyst", "budget": 9})
    text = w.health.health().now_text
    assert "errors in the last 15 min: 1" in text and "  10:02:30 ceo            delegate → ceo/analyst REFUSED: not enough budget" in text


def test_the_answer_is_kept_while_nothing_changes_and_made_again_after_a_while(w: DashWorld) -> None:
    agents_known(w)
    snap = w.snapshots.snapshot()
    first = w.health.health(snap)
    w.analyzer.put(healthy("ops", stuck="x"))
    assert w.health.health(snap) is first
    w.clock.advance(9)
    assert w.health.health(snap).flagged == [("ops", [("stuck", "x")])]


def test_the_checks_are_run_on_demand_and_the_result_is_remembered(w: DashWorld) -> None:
    when, text, ok = w.health.run_check()
    assert when == stamp(200) and ok and "FAIL" not in text
    assert w.state.check_result == (when, text, ok)


def test_a_failed_check_is_a_result_that_says_which(w: DashWorld) -> None:
    team(w)  # the agents hold runs that no message accounts for
    _, text, ok = w.health.run_check()
    assert not ok and "FAIL" in text
