"""Contract of ``EventQueries``: the merged raw stream of the event files, filtered; over event files on disk and in memory.

The stream is what the runtime wrote, as a live system leaves it: several processes, several days, a line being written, kinds and fields from
the future. ``events_view`` is the answer with its counts; ``events`` the events alone; ``follow`` the new ones as they come."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.observability import EventQueries
from orgmcp.observability.testing import IMPLEMENTATIONS, ObservabilityWorld

from . import _support
from ._support import at, items, kinds, stamp


SINCE = "2026-10-18T00:00:00Z"
NOW = stamp(500)


@pytest.fixture(params=_support.implementations(IMPLEMENTATIONS[EventQueries]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ObservabilityWorld:
    made: ObservabilityWorld = request.param(tmp_path)
    assert isinstance(made.events, EventQueries)
    return made


def test_a_log_without_events_is_empty_and_not_an_error(w: ObservabilityWorld) -> None:
    assert w.events.events(now=NOW) == []
    assert w.events.events_view(now=NOW)["total"] == 0


def test_the_view_counts_what_matched_and_what_is_shown(w: ObservabilityWorld) -> None:
    for i in range(5):
        w.tool(i + 1, "ceo", "read")
    view = w.events.events_view(since=SINCE, limit=2, now=NOW)
    assert (view["total"], view["shown"]) == (5, 2) and [e["ts"] for e in items(view)] == [stamp(4).isoformat(), stamp(5).isoformat()]
    assert set(view) == {"events", "total", "shown", "since", "until"}


def test_the_files_of_all_processes_are_merged_by_time_and_damage_is_tolerated(w: ObservabilityWorld) -> None:
    w.tool(10, "ceo", "read", pid=1)
    w.emit(5, "run.start", proc="scheduler", pid=2, run="ceo@x", agent="ceo", batch=[], traces=[])
    w.tool(20, "ceo", "write", pid=1)
    w.emit(15, "scheduler.heartbeat", proc="scheduler", pid=2, running=[], brand_new_field=1)
    w.emit(12, "kind.from.the.future", proc="cli", pid=3, whatever={"x": 1})
    w.partial_line()  # a line being written
    got = w.events.events(since=SINCE, now=NOW)
    assert [at(e["ts"]) for e in got] == sorted(at(e["ts"]) for e in got) and len(got) == 5
    assert kinds(got) == ["run.start", "tool.call", "kind.from.the.future", "scheduler.heartbeat", "tool.call"]


def test_the_window_selects_the_day_directories_first(w: ObservabilityWorld) -> None:
    w.tool(-86400 * 3, "ceo", "old")
    w.tool(0, "ceo", "today")
    w.tool(86400 * 2, "ceo", "later")
    assert [e["tool"] for e in w.events.events(since=stamp(-3600), until=stamp(3600), now=NOW)] == ["today"]
    assert [e["tool"] for e in w.events.events(since="2026-10-10T00:00:00Z", now=stamp(86400 * 3))] == ["old", "today", "later"]


def test_since_and_until_may_be_durations_before_now(w: ObservabilityWorld) -> None:
    for offset in (0, 3000, 3500, 3590):
        w.tool(offset, "ceo", f"t{offset}")
    view = w.events.events_view(since="15m", until="now", now=stamp(3600))
    assert [e["tool"] for e in items(view)] == ["t3000", "t3500", "t3590"]
    assert view["since"] == stamp(3600 - 900).isoformat() and view["until"] == stamp(3600).isoformat()


def test_an_unreadable_time_is_refused_with_the_forms_that_are_read(w: ObservabilityWorld) -> None:
    with pytest.raises(OrgError, match="cannot read 'soon' as a time: use a duration like 15m, 24h, 7d or an ISO timestamp"):
        w.events.events_view(since="soon", now=NOW)


def test_the_kind_filter_matches_the_kind_or_its_prefix(w: ObservabilityWorld) -> None:
    w.tool(1, "ceo", "read")
    w.emit(2, "run.start", proc="scheduler", pid=2, run="ceo@x", agent="ceo", batch=[], traces=[])
    w.emit(3, "run.end", proc="scheduler", pid=2, run="ceo@x", agent="ceo", ok=True)
    w.emit(4, "runtime.thing", proc="scheduler", pid=2)
    assert kinds(w.events.events(since=SINCE, kind="run", now=NOW)) == ["run.start", "run.end"]
    assert kinds(w.events.events(since=SINCE, kind="run.*", now=NOW)) == ["run.start", "run.end"]
    assert kinds(w.events.events(since=SINCE, kind="run.end", now=NOW)) == ["run.end"]


def test_the_agent_filter_matches_the_actor_the_agent_and_both_ends_of_a_message(w: ObservabilityWorld) -> None:
    w.tool(1, "ceo/eng", "read")
    w.emit(2, "agent.pause", proc="scheduler", pid=2, agent="ceo/eng", reason="failures")
    w.emit(3, "stall.nudge", proc="scheduler", pid=2, to="ceo/eng", task="t")
    w.emit(4, "msg.deliver", proc="mcp", pid=3, **{"from": "ceo/eng"}, to="root")
    w.tool(5, "ceo", "read")
    assert kinds(w.events.events(since=SINCE, agent="ceo/eng", now=NOW)) == ["tool.call", "agent.pause", "stall.nudge", "msg.deliver"]
    assert [e["tool"] for e in w.events.events(since=SINCE, agent=" ceo/ ", now=NOW) if "tool" in e] == ["read"]  # the address is normalized


def test_the_trace_filter_matches_the_trace_and_the_traces_of_an_event(w: ObservabilityWorld) -> None:
    w.tool(1, "ceo", "a", trace="T1")
    w.tool(2, "ceo", "b", trace="T2")
    w.emit(3, "run.start", proc="scheduler", pid=2, run="ceo@x", agent="ceo", batch=[], traces=["T1", "T2"])
    assert [e.get("tool") or e["kind"] for e in w.events.events(since=SINCE, trace="T1", now=NOW)] == ["a", "run.start"]
    assert [e.get("tool") or e["kind"] for e in w.events.events(since=SINCE, trace="T2", now=NOW)] == ["b", "run.start"]


def test_errors_are_what_went_wrong(w: ObservabilityWorld) -> None:
    w.tool(1, "ceo", "fine")
    w.tool(2, "ceo", "refused", ok=False, error="no")
    w.emit(3, "cli.command", proc="cli", pid=3, ok=False, command="x")
    w.emit(4, "run.end", proc="scheduler", pid=2, run="a@1", ok=True, timed_out=True)
    w.emit(5, "run.end", proc="scheduler", pid=2, run="a@2", ok=True, killed=True)
    w.emit(6, "run.end", proc="scheduler", pid=2, run="a@3", ok=True)
    w.emit(7, "scheduler.error", proc="scheduler", pid=2, phase="x", error="boom")
    w.emit(8, "run.orphan", proc="scheduler", pid=2, run="a@4", action="killed")
    w.emit(9, "agent.failure", proc="scheduler", pid=2, agent="a", count=3)
    w.emit(10, "scheduler.heartbeat", proc="scheduler", pid=2)
    got = w.events.events(since=SINCE, errors=True, now=NOW)
    assert [e["ts"] for e in got] == [stamp(i).isoformat() for i in (2, 3, 4, 5, 7, 8, 9)]


def test_a_limit_keeps_the_last_events_and_total_counts_all_that_matched(w: ObservabilityWorld) -> None:
    for i in range(1, 8):
        w.tool(i, "ceo", f"t{i}")
    assert [e["tool"] for e in w.events.events(since=SINCE, limit=3, now=NOW)] == ["t5", "t6", "t7"]
    assert w.events.events_view(since=SINCE, limit=3, now=NOW)["total"] == 7
    assert w.events.events_view(since=SINCE, limit=0, now=NOW)["shown"] == 7  # no limit


def test_events_is_the_events_of_the_view(w: ObservabilityWorld) -> None:
    for i in range(1, 5):
        w.tool(i, "ceo", f"t{i}")
    assert w.events.events(since=SINCE, agent="ceo", limit=2, now=NOW) == items(w.events.events_view(since=SINCE, agent="ceo", limit=2, now=NOW))


def test_now_defaults_to_the_clock(w: ObservabilityWorld) -> None:
    w.tool(0, "ceo", "x")
    view = w.events.events_view(since="1h")
    assert abs(stamp(0) - timedelta(hours=1) - at(view["since"])) < timedelta(seconds=1)


def test_follow_yields_the_events_written_after_it_started_and_sleeps_between_polls(w: ObservabilityWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    w.tool(1, "ceo", "before")
    slept: list[float] = []

    def sleeper(seconds: float) -> None:
        slept.append(seconds)
        if len(slept) == 1:
            w.tool(2, "ceo", "after")
            w.partial_line()  # incomplete: not yielded
            w.emit(3, "run.start", proc="scheduler", pid=99, run="a@b", agent="a", batch=[], traces=[])  # a new file

    monkeypatch.setattr(w.clock, "sleep", sleeper)
    seen = [e.get("tool") or e["kind"] for e in w.events.follow(poll=0.25, max_polls=3)]
    assert seen == ["after", "run.start"] and slept == [0.25, 0.25]  # no sleep after the last poll


def test_follow_filters_like_the_view(w: ObservabilityWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    def sleeper(seconds: float) -> None:
        w.tool(1, "ceo", "read")
        w.tool(2, "ceo", "write", ok=False, error="no")

    monkeypatch.setattr(w.clock, "sleep", sleeper)
    assert [e["tool"] for e in w.events.follow(errors=True, poll=0, max_polls=3)] == ["write", "write"]  # one per poll; the good reads are not errors
