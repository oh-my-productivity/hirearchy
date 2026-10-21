# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from testkit.clocks import clock_ports
from testkit.reach.hirearchy.core import ROOT
from testkit.mcp_server_world import build_server

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ENG = "ceo/eng"


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class Clock:
    """The Clock of the runtimes, so message ids, `created` stamps and hire times are deterministic."""

    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t

    def at(self, seconds: float) -> None:
        self.t = at(seconds)


@pytest.fixture(autouse=True)
def clock(process_overrides):
    c = Clock()
    process_overrides(clock_ports(c))
    return c


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def test_mcp_health_permissions(org):
    org.hire("ceo", "ops", "Ops", "Operate.")
    root, ceo, eng = (build_server(org, a) for a in (ROOT, "ceo", ENG))
    assert call(root, "health").splitlines()[0] == "3 agents, 0 flagged"  # whole org by default
    assert call(root, "health", agent=ENG).splitlines()[0] == "1 agent, 0 flagged"
    assert call(ceo, "health").splitlines()[0] == "3 agents, 0 flagged"  # own subtree by default
    assert call(ceo, "health", agent="ceo/ops").splitlines()[0] == "1 agent, 0 flagged"
    assert call(eng, "health").splitlines()[0] == "1 agent, 0 flagged"
    assert call(eng, "health", agent=ENG).splitlines()[0] == "1 agent, 0 flagged"
    for who, target in ((eng, "ceo"), (eng, "ceo/ops"), (ceo, ROOT)):
        with pytest.raises(Exception, match="own subtree"):
            call(who, "health", agent=target)
    with pytest.raises(Exception, match="no such agent"):
        call(root, "health", agent="nobody")
