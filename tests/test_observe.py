"""The query half of observability: events, now, trace, metrics, check, the CLI and the MCP tool.

Event files are written by hand (tests/testkit/obs_fixtures.py) exactly per the spec; the emitting module is not imported.
"""

import asyncio
import dataclasses
import json

import pytest
from testkit.obs_fixtures import EventLog, Story, freeze, run_ids, stamp, stamp_trace

from orgmcp import observe
from orgmcp.cli import main
from orgmcp.core import ROOT, Message, Org
from orgmcp.kernel.testing import FakeClock
from orgmcp.server import build_server

NOW = stamp(200)


@pytest.fixture
def org(tmp_path):
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/testkit/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(monkeypatch):
    return freeze(monkeypatch)


@pytest.fixture
def story(org, clock):
    return Story(org, clock)


def test_cli_views_and_json(org, story, capsys, monkeypatch):
    root = str(org.root)
    monkeypatch.setattr("orgmcp.core.utcnow", lambda: NOW)  # the command line opens its own Org: the clock of its runtime is the patch point
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

    monkeypatch.setattr("orgmcp.cli_obs.time.sleep", interrupt)
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

    monkeypatch.setattr("orgmcp.cli_obs.time.sleep", sleeper)
    main(["--root", str(org.root), "obs", "events", "--since", "2026-10-01T00:00:00Z", "--follow"])
    out = capsys.readouterr().out
    assert "tool.call read" in out and "tool.call write" in out


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def test_observe_tool_is_root_only_and_read_only(org, story):
    org.runtime = dataclasses.replace(org.runtime, clock=FakeClock(NOW))
    root = build_server(org, ROOT)
    names = {t.name for t in asyncio.run(root.list_tools())}
    assert "observe" in names
    assert "observe" not in {t.name for t in asyncio.run(build_server(org, "ceo").list_tools())}
    assert "observe" not in {t.name for t in asyncio.run(build_server(org, "ceo/eng").list_tools())}
    assert "scheduler:" in call(root, "observe")
    assert "totals: wall" in call(root, "observe", view="trace", target=story.task.id)
    assert "all checks passed" in call(root, "observe", view="check")
    assert "tool.call" in call(root, "observe", view="events", target="ceo", since="2026-10-18T00:00:00Z", limit=5)
    assert call(root, "observe", view="metrics", since="2026-10-18T00:00:00Z", by="tool").count("by tool:") == 1
    with pytest.raises(Exception, match="trace needs target"):
        call(root, "observe", view="trace")


def test_observe_tool_docstring_is_short_and_says_read_only():
    from orgmcp import observe as o

    class Fake:
        tools = {}

        def tool(self):
            def deco(fn):
                Fake.tools[fn.__name__] = fn
                return fn

            return deco

    o.register_observe_tool(Fake(), None)
    doc = Fake.tools["observe"].__doc__
    assert doc.startswith("Read-only") and len(doc) < 900
    for view in ("now", "trace", "metrics", "events", "check"):
        assert view in doc


def test_stamp_trace_helper_roundtrips_through_the_loader(org, clock):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    stamp_trace(org, task.id, task.id)
    loaded = Message.load(next((org.dir("ceo") / "inbox").glob("*.md")))
    assert loaded.id == task.id  # the core loader ignores the unknown key
    assert observe.build_messages(observe.scan_messages(org))[task.id].trace == task.id


def test_run_ids_helper(org, clock):
    clock.at(0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    org.begin_run("ceo")
    p = org.start_run_log("ceo")
    assert run_ids(org, "ceo") == [f"ceo@{p.stem}"]
