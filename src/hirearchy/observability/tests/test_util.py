"""The small helpers of the views: times as text, millisecond differences, statistics, JSON-able copies, capped lists, event matchers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hirearchy.kernel import JsonObject
from hirearchy.observability._util import cap, iso, matcher, ms_between, plain, stats

from ._support import stamp



def test_a_time_is_iso_in_utc_and_nothing_is_nothing() -> None:
    assert iso(stamp(0)) == "2026-10-18T10:00:00+00:00" and iso(None) is None
    assert iso(datetime(2026, 10, 18, 12, tzinfo=timezone(timedelta(hours=2)))) == "2026-10-18T10:00:00+00:00"


def test_the_difference_of_two_times_is_in_milliseconds_and_may_be_negative() -> None:
    assert ms_between(stamp(0), stamp(1.5)) == 1500.0 and ms_between(stamp(2), stamp(0)) == -2000.0


def test_statistics_have_the_count_the_nearest_ranks_and_the_maximum() -> None:
    assert stats([]) == {"n": 0, "p50": None, "p95": None, "max": None}
    assert stats([30.0, 10.0, 20.0]) == {"n": 3, "p50": 20.0, "p95": 30.0, "max": 30.0}


def test_a_json_able_copy_turns_times_tuples_sets_and_paths_into_text_and_lists() -> None:
    value = {"t": stamp(0), "tuple": (1, stamp(1)), "set": {3}, "path": Path("/a/b"), 7: [None, "x", 1.5, True], "nested": {"p": (Path("c"),)}}
    assert plain(value) == {"t": "2026-10-18T10:00:00+00:00", "tuple": [1, "2026-10-18T10:00:01+00:00"], "set": [3], "path": "/a/b",
                            "7": [None, "x", 1.5, True], "nested": {"p": ["c"]}}
    assert plain(datetime(2026, 10, 18, 12, tzinfo=timezone(timedelta(hours=2)))) == "2026-10-18T10:00:00+00:00"


def test_a_list_is_capped_with_a_line_that_says_how_to_narrow() -> None:
    lines = [str(i) for i in range(10)]
    assert cap(lines, None, "x") is lines and cap(lines, 10, "x") is lines
    assert cap(lines, 3, "since/agent") == ["0", "1", "2", "... 7 more line(s), narrow with since/agent"]
    assert cap([], 0, "x") == []


def hits(match: Callable[[JsonObject], bool], *events: JsonObject) -> list[bool]:
    return [match(e) for e in events]


def test_the_matcher_without_filters_takes_everything() -> None:
    assert hits(matcher(), {"kind": "x"}, {}) == [True, True]


def test_the_matcher_by_kind_takes_the_kind_and_its_children() -> None:
    events: list[JsonObject] = [{"kind": k} for k in ("run", "run.start", "run.end", "runtime", "tool.call", "")]
    assert hits(matcher(kind="run."), *events) == [True, True, True, False, False, False]
    assert hits(matcher(kind="tool.*"), {"kind": "tool.call"}) == [True] and hits(matcher(kind="tool.call"), {"kind": "tool"}) == [False]


def test_the_matcher_by_agent_looks_at_four_fields_after_normalizing_the_address() -> None:
    events: list[JsonObject] = [{"actor": "ceo/eng"}, {"agent": "ceo/eng"}, {"from": "ceo/eng"}, {"to": "ceo/eng"}, {"actor": "ceo"}, {}]
    assert hits(matcher(agent=" ceo/eng/ "), *events) == [True, True, True, True, False, False]


def test_the_matcher_by_trace_takes_the_trace_or_one_of_the_traces() -> None:
    events: list[JsonObject] = [{"trace": "T"}, {"traces": ["A", "T"]}, {"trace": "U", "traces": ["A"]}, {"traces": None}, {}]
    assert hits(matcher(trace="T"), *events) == [True, True, False, False, False]


def test_the_matcher_with_errors_only_takes_errors_and_all_filters_must_hold() -> None:
    events: list[JsonObject] = [
        {"kind": "tool.call", "actor": "ceo", "ok": False}, {"kind": "tool.call", "actor": "ceo", "ok": True}, {"kind": "tool.call", "actor": "eng", "ok": False}]
    assert hits(matcher(agent="ceo", kind="tool", errors=True), *events) == [True, False, False]
