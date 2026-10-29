"""``parse_since``: the ``since`` of ``retro()`` and ``hirearchy retro --since`` is a date, a datetime with an offset or a message id."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hirearchy.kernel import OrgError
from hirearchy.retro import parse_since


def test_a_date_is_local_midnight() -> None:
    assert parse_since("2026-11-02") == datetime(2026, 11, 2).astimezone()


def test_a_datetime_needs_its_offset() -> None:
    assert parse_since("2026-11-02T10:30:00+00:00") == datetime(2026, 11, 2, 10, 30, tzinfo=timezone.utc)
    assert parse_since(" 2026-11-02T10:30:00Z ") == datetime(2026, 11, 2, 10, 30, tzinfo=timezone.utc)
    with pytest.raises(OrgError):
        parse_since("2026-11-02T10:30:00")


def test_a_message_id_is_its_creation_stamp() -> None:
    assert parse_since("20261102T103000123456-1-ab12") == datetime(2026, 11, 2, 10, 30, 0, 123456, tzinfo=timezone.utc)


@pytest.mark.parametrize("bad", ["", "yesterday", "2026-13-40", "11/02/2026", "T-1"])
def test_anything_else_is_refused_with_the_words_of_the_design(bad: str) -> None:
    with pytest.raises(OrgError) as info:
        parse_since(bad)
    assert str(info.value) == f"refused: since must be a date (2026-11-02), a datetime with offset or a message id: {bad}. Nothing was read."
