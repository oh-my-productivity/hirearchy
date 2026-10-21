"""The pure functions of the vocabulary: nearest-rank percentile, times, refusals, what an error is, one line of an event."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import OrgError
from hirearchy.observability import fmt_rel, format_event, is_error, normalize_refusal, parse_when, percentile

from ._support import stamp



def test_percentile_is_nearest_rank_and_exact() -> None:
    vals = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    assert [percentile(vals, p) for p in (50, 95, 10, 100, 0)] == [50.0, 100.0, 10.0, 100.0, 10.0]
    assert percentile([7.0], 95) == 7.0 and percentile([], 50) is None
    assert percentile([3.0, 1.0, 2.0], 50) == 2.0  # unsorted input


def test_parse_when_reads_durations_now_and_iso_timestamps() -> None:
    now = stamp(0)
    assert parse_when("15m", now) == now - timedelta(minutes=15)
    assert parse_when("24h", now) == now - timedelta(hours=24)
    assert parse_when("7d", now) == now - timedelta(days=7)
    assert parse_when("1.5h", now) == now - timedelta(minutes=90)
    assert parse_when("2w", now) == now - timedelta(weeks=2)
    assert parse_when(" NOW ", now) == now
    assert parse_when("2026-10-18T09:00:00Z", now) == stamp(-3600)
    assert parse_when("2026-10-18T09:00:00", now) == stamp(-3600)  # naive = UTC
    assert parse_when("2026-10-18T11:00:00+02:00", now) == stamp(-3600)


def test_parse_when_has_nothing_for_nothing_and_passes_a_time_through() -> None:
    assert parse_when(None, stamp(0)) is None and parse_when("", stamp(0)) is None
    assert parse_when(datetime(2026, 1, 1), stamp(0)) == datetime(2026, 1, 1, tzinfo=timezone.utc)
    other = datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=2)))
    assert parse_when(other, stamp(0)) == other


def test_parse_when_without_now_counts_from_the_wall_clock() -> None:
    got = parse_when("1h")
    assert got is not None and abs((datetime.now(timezone.utc) - timedelta(hours=1)) - got) < timedelta(seconds=5)


def test_parse_when_refuses_what_it_cannot_read() -> None:
    with pytest.raises(OrgError, match="cannot read 'soon' as a time: use a duration like 15m, 24h, 7d or an ISO timestamp like 2026-10-18T10:00:00Z"):
        parse_when("soon", stamp(0))


def test_a_time_within_a_request() -> None:
    assert [fmt_rel(x) for x in (0, -5, 999, 42_000, 65_000, 3_599_000, 7_380_000)] == ["+0s", "+0s", "+0s", "+42s", "+1m05s", "+59m59s", "+2h03m"]


def test_refusals_are_normalized_so_reasons_group() -> None:
    a = normalize_refusal('not enough budget: you have 5 run(s); task 20261018T100003000001-root-ab12 "Ship it" in ceo/work/x.md')
    b = normalize_refusal('not enough budget: you have 9 run(s); task 20261018T110003000001-root-cd34 "Other" in ceo/work/y.md')
    assert a == b == "not enough budget: you have N run(s); task <id> <text> in <path>"
    assert normalize_refusal("hash deadbeef01 at /var/log/x") == "hash <hex> at <path>"
    assert normalize_refusal("zz " * 200).endswith("…") and len(normalize_refusal("zz " * 200)) <= 160
    assert normalize_refusal("two\n\nlines") == "two lines"


@pytest.mark.parametrize(
    ("event", "error"),
    [
        ({"kind": "tool.call", "ok": False}, True),
        ({"kind": "tool.call", "ok": True}, False),
        ({"kind": "tool.call"}, False),  # no verdict is no failure
        ({"kind": "cli.command", "ok": False}, True),
        ({"kind": "run.end", "ok": False}, True),
        ({"kind": "run.end", "ok": True, "timed_out": True}, True),
        ({"kind": "run.end", "ok": True, "killed": True}, True),
        ({"kind": "run.end", "ok": True}, False),
        ({"kind": "scheduler.error"}, True),
        ({"kind": "run.orphan"}, True),
        ({"kind": "agent.failure"}, True),
        ({"kind": "scheduler.heartbeat"}, False),
        ({}, False),
    ],
)
def test_what_counts_as_an_error(event: dict[str, object], error: bool) -> None:
    assert is_error(event) is error


BASE = {"v": 1, "seq": 3, "pid": 4, "ts": "2026-10-18T10:00:07.250000+00:00", "proc": "mcp", "actor": "ceo", "run": None, "trace": None}


def test_a_tool_call_is_one_line_with_its_verdict_and_time() -> None:
    ok = {**BASE, "kind": "tool.call", "tool": "read", "ok": True, "ms": 42, "args": {"path": "a/b"}}
    assert format_event(ok) == "10:00:07.250 mcp ceo tool.call read ok 42ms args=path=a/b"  # blanks are collapsed: the columns are for the width only
    refused = {**BASE, "kind": "tool.call", "tool": "send", "ok": False, "ms": 3, "error": "no way", "error_type": "OrgError"}
    assert format_event(refused) == '10:00:07.250 mcp ceo tool.call send REFUSED 3ms error="no way" error_type=OrgError'
    failed = {**refused, "error_type": "ValueError"}
    assert " send FAILED 3ms " in format_event(failed)


def test_a_run_end_says_how_it_ended() -> None:
    end = {**BASE, "kind": "run.end", "proc": "scheduler", "actor": "runtime", "ok": False, "duration_ms": 61_000, "timed_out": True, "killed": True,
           "exit_code": -9, "run": "ceo@x", "trace": "T1", "error": None}
    assert format_event(end) == "10:00:07.250 scheduler runtime run.end FAILED 1m01s timed-out killed exit_code=-9 run=ceo@x trace=T1"


def test_other_fields_follow_in_order_and_empty_ones_are_left_out() -> None:
    ev = {**BASE, "kind": "stall.nudge", "task": "t1", "to": "ceo", "step": 0, "empty": "", "none": None, "list": [], "map": {}, "traces": ["a", "b"],
          "detail": {"x": 1, "y": "z"}}
    assert format_event(ev) == "10:00:07.250 mcp ceo stall.nudge task=t1 to=ceo step=0 traces=a,b detail=x=1,y=z"


def test_a_line_is_cut_to_the_width_and_a_bad_time_is_shown_as_it_is() -> None:
    long = {**BASE, "kind": "note", "text": "word " * 100}
    assert format_event(long, 80).endswith("…") and len(format_event(long, 80)) == 80
    assert format_event({"kind": "x", "ts": "yesterday-ish and more", "proc": "cli"}) == "yesterday-is cli - x"
    assert format_event({"kind": "x", "ts": "2026-10-18T10:00:07+00:00"}) == "10:00:07 ? - x"  # no microseconds: no fraction
