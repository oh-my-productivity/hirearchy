"""``FixedHealthAnalyzer``: the stand-in for the analyzer that the tests of ``review`` and ``dashdata`` use - the health a test puts in, with the
real analyzer's guards and branch totals."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmcp.agents.testing import MemoryAgents
from orgmcp.health import AgentHealth, HealthAnalyzer
from orgmcp.health.testing import FixedHealthAnalyzer, at
from orgmcp.kernel import OrgError
from orgmcp.kernel.testing import FakeClock

CHARTER = "---\nrole: Worker\n---\n# Role: Worker\n\nDo the work.\n"


def health(addr: str, runs: int = 0, **flags: str) -> AgentHealth:
    return AgentHealth(
        addr=addr, depth=addr.count("/") + 1, state="idle", budget_left=1, budget_received=1, runs_used=runs, tasks_received=0, open_tasks=0,
        oldest_open_age=None, done=0, failed=0, blocked=0, runs_per_task=None, rework=0, empty_runs=0, last_activity=None,
        since_activity=None, flags=dict(flags),
    )


def build() -> tuple[FixedHealthAnalyzer, FakeClock]:
    agents, clock = MemoryAgents(), FakeClock(at(500))
    for addr in ("ceo", "ceo/eng", "ops"):
        agents.put(f"{addr}/AGENT.md", CHARTER)
    return FixedHealthAnalyzer(agents, clock), clock


def test_it_is_an_analyzer() -> None:
    assert isinstance(build()[0], HealthAnalyzer)


def test_an_agent_has_the_health_that_was_put_in() -> None:
    fixed, _ = build()
    eng = health("ceo/eng", idle="quiet")
    fixed.put(eng)
    assert fixed.agent_health(" ceo/eng ", at(1)) is eng


def test_the_guards_are_the_real_ones() -> None:
    fixed, _ = build()
    with pytest.raises(OrgError, match="root is the human"):
        fixed.agent_health("root")
    with pytest.raises(OrgError, match="no such agent: ghost"):
        fixed.agent_health("ghost")
    with pytest.raises(OrgError, match="no such agent: ghost"):
        fixed.org_health("ghost")
    with pytest.raises(OrgError, match="no health was put in for ops"):
        fixed.agent_health("ops")


def test_the_organization_is_the_agents_in_order_with_branch_totals() -> None:
    fixed, clock = build()
    for h in (health("ceo", 1), health("ceo/eng", 2, stuck="old"), health("ops", 4)):
        fixed.put(h)
    report = fixed.org_health()
    assert [h.addr for h in report.agents] == ["ceo", "ceo/eng", "ops"] and report.root == "root"
    assert list(report.branches) == ["root", "ceo", "ceo/eng", "ops"]
    assert (report.branches["root"].runs_used, report.branches["ceo"].runs_used) == (7, 3)
    assert report.branches["ceo"].worst_flag == "stuck" and report.branches["ops"].worst_flag is None
    assert abs((report.now - clock.t).total_seconds()) < 1  # the clock's time when none is given
    given = datetime(2026, 5, 6, 7, 8, 9)
    assert fixed.org_health("ceo", given).now == given.replace(tzinfo=timezone.utc)
    assert [h.addr for h in fixed.org_health("ceo").agents] == ["ceo", "ceo/eng"]
