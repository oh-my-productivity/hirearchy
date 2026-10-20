import asyncio
import json
import os
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


def add_run(org, addr, start, end):
    """A run log named after its start with mtime = its end (seconds after T0)."""
    d = org.dir(addr) / "runs"
    d.mkdir(exist_ok=True)
    p = d / f"{at(start):%Y%m%dT%H%M%S%f}.log"
    p.touch()
    os.utime(p, (at(end).timestamp(), at(end).timestamp()))


def add_runs(org, addr, n, first=100):
    for i in range(n):
        add_run(org, addr, first + i * 100, first + i * 100 + 50)


def give(org, budget=5, to=ENG, **kw):
    """root assigns a task and the assignee reads it (no unread mail left)."""
    task = org.delegate(ROOT, to, "Job", "goal", "acceptance", budget=budget, **kw)
    org.begin_run(to)
    org.end_run(to, ok=True)
    return task


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


# ---------------------------------------------------------- branches and report
@pytest.fixture
def troubled(org):
    """ceo is paused; eng has an old open task nobody works on."""
    give(org)
    org.pause("ceo", "manual")
    add_runs(org, "ceo", 2)
    add_runs(org, ENG, 3, first=200)
    return org


# ----------------------------------------------------------------- CLI and MCP
def test_cli_health(troubled, capsys):
    main(["--root", str(troubled.root), "health"])
    out = capsys.readouterr().out
    assert out.splitlines()[0].endswith("flagged") and "ceo" in out and "eng" in out
    main(["--root", str(troubled.root), "health", "--agent", ENG])
    scoped = capsys.readouterr().out
    assert scoped.splitlines()[0].startswith("1 agent,") and "ceo " not in scoped
    main(["--root", str(troubled.root), "health", "--json"])
    assert [a["addr"] for a in json.loads(capsys.readouterr().out)["agents"]] == ["ceo", ENG]
    with pytest.raises(SystemExit):
        main(["--root", str(troubled.root), "health", "--agent", "nobody"])
    assert "no such agent" in capsys.readouterr().err


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
