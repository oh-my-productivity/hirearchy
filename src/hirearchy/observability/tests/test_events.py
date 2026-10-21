# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit import observability_world as observe
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.obs_fixtures import EventLog, Story, stamp
from testkit.observability_world import freeze


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
def clock(org):
    return freeze(org)


@pytest.fixture
def story(org, clock):
    return Story(org, clock)


# ------------------------------------------------------------------------------------------------ events
def test_events_merge_files_by_time_and_tolerate_damage(org):
    log = EventLog(org)
    log.emit("tool.call", stamp(10), proc="mcp", pid=1, actor="ceo", tool="read", ok=True, ms=1, error=None, error_type=None, args={})
    log.emit("run.start", stamp(5), proc="scheduler", pid=2, run="ceo@x", agent="ceo", batch=[], traces=[])
    log.emit("tool.call", stamp(20), proc="mcp", pid=1, actor="ceo", tool="write", ok=True, ms=1, error=None, error_type=None, args={})
    log.emit("scheduler.heartbeat", stamp(15), proc="scheduler", pid=2, running=[], runnable=0, waiting_on_you=0, brand_new_field=1)
    log.emit("kind.from.the.future", stamp(12), proc="cli", pid=3, whatever={"x": 1})
    log.partial_line("mcp", 1, "2026-10-18")  # a line being written
    (org.root / ".runtime" / "events" / "2026-10-18" / "notes.txt").write_text("not an event file")
    (org.root / ".runtime" / "events" / "scratch").mkdir()
    got = observe.events(org, since="2026-10-18T00:00:00Z")
    assert [e["ts"] for e in got] == sorted(e["ts"] for e in got) and len(got) == 5
    assert [e["kind"] for e in got][:2] == ["run.start", "tool.call"]
    assert "kind.from.the.future" in [e["kind"] for e in got]


def test_events_without_any_files_is_empty_not_an_error(org):
    assert observe.events(org) == []
    assert "no matching events" in observe.render_events(observe.events_view(org))


def test_events_time_window_selects_day_directories_first(org):
    log = EventLog(org)
    log.emit("tool.call", stamp(-86400 * 3), actor="ceo", tool="old", ok=True, ms=1)  # 3 days earlier
    log.emit("tool.call", stamp(0), actor="ceo", tool="today", ok=True, ms=1)
    log.emit("tool.call", stamp(86400 * 2), actor="ceo", tool="later", ok=True, ms=1)
    days = {p.parent.name for p in observe.event_files(org, stamp(-3600), stamp(3600))}
    assert days == {"2026-10-18"}
    assert [e["tool"] for e in observe.events(org, since=stamp(-3600), until=stamp(3600))] == ["today"]
    assert [e["tool"] for e in observe.events(org, since="2026-10-10T00:00:00Z", now=stamp(86400 * 3))] == ["old", "today", "later"]


def test_events_filters_and_limit_keep_the_tail(org, story):
    tid = story.task.id
    assert {e["kind"] for e in observe.events(org, kind="run")} == {"run.start", "run.end"}
    assert {e["kind"] for e in observe.events(org, kind="tool.call")} == {"tool.call"}
    assert all(e["actor"] == "ceo/eng" for e in observe.events(org, kind="tool.call", agent="ceo/eng"))
    assert {e["agent"] for e in observe.events(org, kind="run.start", agent="ceo")} == {"ceo"}
    traced = observe.events(org, trace=tid)
    assert traced and all(e["trace"] == tid or tid in (e.get("traces") or []) for e in traced)
    errs = observe.events(org, errors=True)
    assert len(errs) == 1 and "not enough budget" in errs[0]["error"]
    last2 = observe.events(org, limit=2)
    assert len(last2) == 2 and last2[-1]["kind"] == "scheduler.exit"  # the tail of the stream
    allv = observe.events_view(org, limit=3)
    assert allv["shown"] == 3 and allv["total"] > 3
    assert "earlier one(s) not shown" in observe.render_events(allv)


def test_every_refused_tool_call_is_in_errors_with_its_text(org, clock):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "send", ok=False, error="ceo cannot message root-x: not allowed")
    log.tool(stamp(2), "ceo", "send", ok=True)
    log.emit("tool.call", stamp(3), actor="ceo", tool="read", ok=False, ms=1, error="ZeroDivisionError: x", error_type="ZeroDivisionError")
    errs = observe.events(org, errors=True)
    assert [e["error"] for e in errs] == ["ceo cannot message root-x: not allowed", "ZeroDivisionError: x"]
    assert "REFUSED" in observe.format_event(errs[0]) and "not allowed" in observe.format_event(errs[0])
    assert "FAILED" in observe.format_event(errs[1])


def test_follow_prints_only_new_lines_across_files(org, clock):
    log = EventLog(org)
    log.tool(stamp(1), "ceo", "read")
    seen = []

    def sleeper(_):
        n = len(seen)
        if n == 0:
            log.tool(stamp(2), "ceo", "write")  # appended to an existing file
        elif n == 1:
            log.emit("run.start", stamp(3), proc="scheduler", pid=99, run="a@b", agent="a", batch=[], traces=[])  # a new file
            log.partial_line("mcp", 4242, "2026-10-18", '{"v": 1, "ts"')  # incomplete: not yielded

    gen = observe.follow_events(org, poll=0, sleep=sleeper, max_polls=4)
    for ev in gen:
        seen.append(ev["kind"])
    assert seen == ["tool.call", "run.start"] and "read" not in str(seen)


def test_follow_filters(org, clock):
    log = EventLog(org)
    out = []

    def sleeper(_):
        log.tool(stamp(1), "ceo", "read")
        log.tool(stamp(2), "ceo", "write", ok=False, error="no")

    for ev in observe.follow_events(org, errors=True, poll=0, sleep=sleeper, max_polls=3):
        out.append(ev["tool"])
    assert out == ["write", "write"]  # one per poll; the successful reads are filtered out


def test_runs_of_agents_that_no_longer_exist_are_known_from_events(org, clock):
    log = EventLog(org)
    log.run("gone/agent", "20261018T100100000000", stamp(60), 12, ["20261018T100000000000-root-ab12"], [], pid=1)
    m = observe.metrics(org, since="2026-10-18T00:00:00Z", by="agent", now=stamp(500))
    assert m["runs"]["total"] == 1 and m["by"]["rows"][0]["key"] == "gone/agent"
    assert m["runs"]["duration_ms"]["p50"] == 12_000 and m["runs"]["queue_ms"]["p50"] == pytest.approx(60_005, abs=10)
