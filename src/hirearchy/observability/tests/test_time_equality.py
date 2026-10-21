"""``observe._ts`` is deleted: ``kernel.parse_time`` answers the same for every input (ARCHITECTURE.md 5.10).

``_ts`` is copied here as it was in ``observe.py``; ``_aware`` and ``_stamp`` (``health``'s, which ``observe`` imported) are the kernel's ``aware`` and
``stamp_of``: the same code under another name. This proof needs no code of the package, so it is not red."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from hirearchy.kernel import aware, parse_time, stamp_of


def _aware(t: datetime | None) -> datetime | None:
    return t if t is None or t.tzinfo else t.replace(tzinfo=timezone.utc)


def old_ts(value: object) -> datetime | None:
    """``observe._ts`` before the move."""
    try:
        return _aware(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


INPUTS = [
    "2026-10-18T10:00:07.250000+00:00", "2026-10-18T10:00:07+00:00", "2026-10-18T10:00:07", "2026-10-18 10:00:07", "2026-10-18T10:00:07Z",
    "2026-10-18T12:00:07+02:00", "2026-10-18", "20261018T100007", "", "soon", "None", "10:00", "2026-13-45T00:00:00", " 2026-10-18T10:00:07 ",
    None, 0, 12.5, True, b"2026-10-18", ["2026-10-18"], {"ts": 1},
    datetime(2026, 10, 18, 10, 0, 7), datetime(2026, 10, 18, 10, 0, 7, 250000, tzinfo=timezone.utc),
    datetime(2026, 10, 18, 12, 0, 7, tzinfo=timezone(timedelta(hours=2))), datetime(2026, 10, 18, 10, 0, 7, fold=1), date(2026, 10, 18),
]


@pytest.mark.parametrize("value", INPUTS, ids=[repr(v)[:40] for v in INPUTS])
def test_parse_time_answers_what_the_old_function_did(value: object) -> None:
    assert parse_time(value) == old_ts(value)
    got = parse_time(value)
    assert got is None or got.tzinfo is not None  # aware, like before


def test_the_other_two_names_are_the_kernels() -> None:
    naive = datetime(2026, 10, 18, 10)
    assert aware(naive) == _aware(naive) and aware(None) is None
    assert stamp_of("20261018T100003000001-root-ab12") == stamp_of("20261018T100003000001.log") == datetime(2026, 10, 18, 10, 0, 3, 1, tzinfo=timezone.utc)
    assert stamp_of("short") is None
