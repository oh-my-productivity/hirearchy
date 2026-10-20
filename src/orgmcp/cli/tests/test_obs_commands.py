# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json

import pytest
from testkit.cli_world import SleepingClock, cli_clocked, clock_is, main
from testkit.legacy.orgmcp.core import ROOT, Org
from testkit.obs_fixtures import EventLog, Story, stamp

from orgmcp.kernel.testing import FakeClock

NOW = stamp(200)


@pytest.fixture
def org(tmp_path, clock):
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/testkit/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py. Built under the frozen ``clock`` (the hand-written events are dated
    from its origin), as is every organization the command line opens."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(process_overrides):
    return clock_is(process_overrides, FakeClock())


@pytest.fixture
def story(org, clock):
    return Story(org, clock)


def test_cli_views_and_json(org, story, capsys, process_overrides):
    root = str(org.root)
    clock_is(process_overrides, FakeClock(NOW))  # the command line opens its own Org: its runtime gets the clock of the providers
    main(["--root", root, "obs", "trace", story.task.id])
    assert "totals: wall" in capsys.readouterr().out
    main(["--root", root, "obs", "trace", story.task.id, "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["totals"]["runs"] == 3 and data["task"] == story.task.id
    main(["--root", root, "obs", "metrics", "--since", "2026-10-18T00:00:00Z", "--by", "agent", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["runs"]["total"] == 3 and out["by"]["dimension"] == "agent"
    main(["--root", root, "obs", "events", "--since", "2026-10-18T00:00:00Z", "--errors", "--json"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["tool"] == "delegate"
    main(["--root", root, "obs", "events", "--since", "2026-10-18T00:00:00Z", "--kind", "run.end", "--limit", "2"])
    assert "2 of 3 matching event(s)" in capsys.readouterr().out
    main(["--root", root, "obs", "now"])
    assert "scheduler:" in capsys.readouterr().out
    main(["--root", root, "obs", "now", "--json"])
    assert json.loads(capsys.readouterr().out)["scheduler"]["state"] == "stopped"
    main(["--root", root, "check", "--json"])
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_cli_check_exits_1_on_a_failure(org, capsys):
    (org.root / ".runtime" / "scheduler.pid").write_text("999999")
    with pytest.raises(SystemExit) as exc:
        main(["--root", str(org.root), "check"])
    assert exc.value.code == 1 and "FAIL" in capsys.readouterr().out


def test_cli_errors_are_plain_messages(org, capsys):
    with pytest.raises(SystemExit):
        main(["--root", str(org.root), "obs", "trace", "nope"])
    assert "error: no message nope" in capsys.readouterr().err


def test_cli_watch_and_follow_exit_cleanly_on_ctrl_c(org, story, capsys, monkeypatch):
    def interrupt(_):
        raise KeyboardInterrupt

    main = cli_clocked(SleepingClock(interrupt))
    main(["--root", str(org.root), "obs", "now", "--watch", "5"])
    assert "scheduler:" in capsys.readouterr().out
    main(["--root", str(org.root), "obs", "events", "--since", "2026-10-18T00:00:00Z", "--limit", "1", "--follow"])
    assert "matching event" in capsys.readouterr().out


def test_cli_follow_prints_new_events(org, clock, capsys, monkeypatch):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "read")
    calls = []

    def sleeper(_):
        if not calls:
            calls.append(1)
            log.tool(stamp(2), "ceo", "write")
        else:
            raise KeyboardInterrupt

    main = cli_clocked(SleepingClock(sleeper))
    main(["--root", str(org.root), "obs", "events", "--since", "2026-10-01T00:00:00Z", "--follow"])
    out = capsys.readouterr().out
    assert "tool.call read" in out and "tool.call write" in out
