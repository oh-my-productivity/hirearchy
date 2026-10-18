"""Time vocabulary. Oracle tests: for tables of >= 200 inputs the kernel helpers give exactly what the legacy ones gave
(same value, or the same exception type)."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

import pytest

from orgmcp.kernel import Message, aware, fmt_dur, fmt_duration, msg_time, parse_time, stamp_of
from orgmcp.kernel.tests import _oracle
from orgmcp.kernel.tests._legacy import legacy

UTC = timezone.utc


def outcome(fn: Callable[..., object], arg: object) -> tuple[str, object]:
    """The result of ``fn(arg)``, or the type of the exception it raised (so errors are compared too)."""
    try:
        return "value", fn(arg)
    except Exception as exc:  # noqa: BLE001 - the oracle compares failures as well
        return "raises", type(exc).__name__


def same(new: Callable[..., object], old: Callable[..., object], table: list[object]) -> None:
    assert len(table) >= 200
    for arg in table:
        assert outcome(new, arg) == outcome(old, arg), f"differs for {arg!r}"


def _datetimes() -> list[datetime]:
    rnd = random.Random(20261018)
    base = [datetime(2026, 10, 18, 10, 0, 0), datetime(1970, 1, 1), datetime(2000, 2, 29, 23, 59, 59, 999999), datetime(9999, 12, 31, 23, 59, 59)]
    base += [datetime(2020, 1, 1) + timedelta(seconds=rnd.randrange(0, 10**9), microseconds=rnd.randrange(10**6)) for _ in range(60)]
    return base


def test_aware_attaches_utc_only_when_there_is_no_zone() -> None:
    naive = datetime(2026, 10, 18, 10, 0, 0)
    assert aware(naive) == naive.replace(tzinfo=UTC) and aware(naive).tzinfo is UTC
    other = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert aware(other) is other
    assert aware(None) is None


def test_aware_oracle() -> None:
    zones = [None, UTC, timezone(timedelta(hours=5, minutes=30)), timezone(timedelta(hours=-8))]
    table: list[object] = [None] + [d.replace(tzinfo=z) for d in _datetimes() for z in zones]
    same(aware, _oracle._aware, table)
    same(aware, legacy("health")._aware, table)


def _parse_inputs() -> list[object]:
    out: list[object] = []
    for d in _datetimes():
        out += [d, d.replace(tzinfo=UTC), d.isoformat(), d.replace(tzinfo=UTC).isoformat(), d.isoformat(timespec="seconds"),
                d.replace(tzinfo=timezone(timedelta(hours=-3))).isoformat(), d.isoformat(sep=" "), str(d.date()), d.isoformat() + "Z"]
    out += ["", " ", "None", "yesterday", "2026-13-01", "2026-10-18T25:00:00", "20261018T100000", "2026-10-18T10:00",
            "2026-10-18T10:00:00+02:00", "2026-10-18T10:00:00Z", "10:00", "2026", None, 0, 17.5, True, [], {}, date(2026, 10, 18), b"x"]
    return out


def test_parse_time_accepts_iso_strings_and_datetimes() -> None:
    assert parse_time("2026-10-18T10:00:00") == datetime(2026, 10, 18, 10, 0, tzinfo=UTC)
    assert parse_time("2026-10-18T10:00:00+02:00") == datetime(2026, 10, 18, 8, 0, tzinfo=UTC)
    assert parse_time(datetime(2026, 10, 18, 10, 0)) == datetime(2026, 10, 18, 10, 0, tzinfo=UTC)
    assert parse_time("not a time") is None and parse_time(None) is None and parse_time("") is None


def test_parse_time_oracle() -> None:
    table = _parse_inputs()
    same(parse_time, _oracle._parse_time, table)
    same(parse_time, legacy("health")._parse_time, table)


def _stamp_inputs() -> list[object]:
    rnd = random.Random(7)
    out: list[object] = []
    for d in _datetimes():
        s = f"{d:%Y%m%dT%H%M%S%f}"
        out += [s, f"{s}-ceo-ab12", f"{s}-ceo.eng-ab12.md", f"{s}.log", f".{s}", s[:-1], s + "9"]
    out += ["", "2026", "x" * 21, "20261318T100000000001", "20261018T250000000001", "20261018T100000000001-root-0000",
            "2026-10-18T10:00:00", "20261018 100000000001", " 20261018T100000000001"]
    out += ["".join(rnd.choice("0123456789T-.") for _ in range(rnd.randrange(0, 30))) for _ in range(20)]
    return out


def test_stamp_of_reads_the_timestamp_prefix() -> None:
    assert stamp_of("20261018T100000000001-root-ab12.md") == datetime(2026, 10, 18, 10, 0, 0, 1, tzinfo=UTC)
    assert stamp_of("nonsense") is None and stamp_of("") is None and stamp_of(".20261018T100000000001") is None


def test_stamp_of_oracle() -> None:
    table = _stamp_inputs()
    same(stamp_of, _oracle._stamp, table)
    same(stamp_of, legacy("health")._stamp, table)


def _messages() -> list[object]:
    rnd = random.Random(11)
    ids = ["20261018T100000000001-root-ab12", "20261018T100000000001", "garbage", "", "short", ".20261018T100000000001-x-1"]
    created = ["2026-10-18T10:00:00", "2026-10-18T10:00:00Z", "2026-10-18 10:00:00+01:00", "", "garbage", "2026-10-18", "None", "20261018T100000"]
    out: list[object] = [Message("a", "b", "note", "", id=i, created=c) for i in ids for c in created]
    for _ in range(160):
        d = rnd.choice(_datetimes())
        out.append(Message("a", "b", "note", "", id=rnd.choice([f"{d:%Y%m%dT%H%M%S%f}-a-ab12", "x", ""]), created=rnd.choice([d.isoformat(), "", "?"])))
    return out


def test_msg_time_prefers_the_id_over_created() -> None:
    both = Message("a", "b", "note", "", id="20261018T100000000001-a-ab12", created="2020-01-01T00:00:00")
    assert msg_time(both) == datetime(2026, 10, 18, 10, 0, 0, 1, tzinfo=UTC)
    only_created = Message("a", "b", "note", "", id="nope", created="2026-10-18T10:00:00")
    assert msg_time(only_created) == datetime(2026, 10, 18, 10, 0, tzinfo=UTC)
    assert msg_time(Message("a", "b", "note", "", id="nope")) is None


def test_msg_time_oracle() -> None:
    table = _messages()
    same(msg_time, _oracle._msg_time, table)
    same(msg_time, legacy("health")._msg_time, table)


def _seconds() -> list[object]:
    rnd = random.Random(3)
    out: list[object] = [None, 0, 0.0, 0.9, 1, 59, 59.99, 60, 61, 3599, 3600, 3661, 86399, 86400, 172800.5, 10**7, -5, -0.5,
                         float("nan"), float("inf"), True, "90", "x", [], 1e15]
    out += [rnd.uniform(0, 10**6) for _ in range(120)] + [rnd.randrange(0, 200) for _ in range(40)] + [rnd.uniform(-100, 100) for _ in range(20)]
    return out


def test_fmt_duration_is_coarse() -> None:
    assert [fmt_duration(s) for s in (None, 0, 45, 60, 419, 3600, 86400 * 2 + 5)] == ["0s", "0s", "45s", "1m", "6m", "1h", "2d"]


def test_fmt_duration_oracle() -> None:
    table = _seconds()
    same(fmt_duration, _oracle._duration, table)
    same(fmt_duration, legacy("health")._duration, table)


def _millis() -> list[object]:
    rnd = random.Random(5)
    out: list[object] = [None, 0, 0.0, 0.4, 0.5, 1, 999, 999.4, 999.5, 1000, 1049, 1050, 9949, 9950, 9999, 10000, 10499, 10500, 59499,
                         59500, 59999, 60000, 65000, 3599499, 3599500, 3600000, 7380000, 10**9, -1, -1000, "850", True, float("nan"), float("inf")]
    out += [rnd.uniform(0, 5000) for _ in range(50)] + [rnd.uniform(0, 10**7) for _ in range(120)] + [rnd.uniform(-10, 10) for _ in range(10)]
    return out


def test_fmt_dur_shapes() -> None:
    assert [fmt_dur(ms) for ms in (None, 0, 850, 4200, 42000, 65000, 7380000)] == ["?", "0s", "850ms", "4.2s", "42s", "1m05s", "2h03m"]


def test_fmt_dur_oracle() -> None:
    table = _millis()
    same(fmt_dur, legacy("observe").fmt_dur, table)  # the legacy implementation is still there: compared live
