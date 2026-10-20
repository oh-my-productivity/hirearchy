# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from testkit.clocks import clock_ports
from testkit.legacy.orgmcp.core import ROOT
from testkit.mcp_server_world import build_server, main

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


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


def test_revises_through_the_mcp_tool_and_cli(org, capsys):
    first = org.delegate(ROOT, "ceo", "Plan", "g", "a")
    out = call(build_server(org, ROOT), "delegate", to="ceo", title="Plan 2", goal="g", acceptance="a",
               revises=first.id)
    assert "delegated" in out
    main(["--root", str(org.root), "task", "ceo", "--title", "Plan 3", "--goal", "g", "--acceptance", "a",
          "--revises", first.id])
    assert capsys.readouterr().out.startswith("task ")
    assert sum(1 for m in org.received("ceo") if m.revises == first.id) == 2
    with pytest.raises(SystemExit):
        main(["--root", str(org.root), "task", "ceo", "--title", "x", "--goal", "g", "--acceptance", "a",
              "--revises", "bogus"])
    assert "revises" in capsys.readouterr().err
