# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from testkit.cli_world import clock_is, main
from testkit.legacy.orgmcp.core import ROOT

from orgmcp.kernel.testing import FakeClock

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ENG = "ceo/eng"


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class Clock(FakeClock):
    """The clock of every runtime of the test, so message ids, `created` stamps and hire times are deterministic: it stands still."""

    def __init__(self):
        super().__init__(T0)

    def now(self):
        return self.t

    def at(self, seconds: float) -> None:
        self.t = at(seconds)


@pytest.fixture(autouse=True)
def clock(process_overrides):
    c = Clock()
    clock_is(process_overrides, c)
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
