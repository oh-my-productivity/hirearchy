import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from orgmcp import core
from orgmcp.cli import main
from orgmcp.core import ROOT
from orgmcp.server import build_server

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ENG = "ceo/eng"


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class Clock:
    """Replaces core.utcnow so message ids, `created` stamps and hire times are deterministic."""

    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t

    def at(self, seconds: float) -> None:
        self.t = at(seconds)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(core, "utcnow", c)
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
