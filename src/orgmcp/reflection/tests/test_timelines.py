"""``StorePlaybookTimelines``: when each version of a playbook was written, from the history the store keeps."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmcp.kernel import JsonObject
from orgmcp.reflection._ports import PlaybookHistory, PlaybookTimelines
from orgmcp.reflection._timeline import StorePlaybookTimelines

RED = pytest.mark.xfail(strict=True, reason="red: C-reflection")

T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)


class History(PlaybookHistory):
    def __init__(self, found: list[tuple[int, JsonObject]]) -> None:
        self._found = found

    def playbook_history(self, owner: str, name: str) -> list[tuple[int, JsonObject]]:
        return self._found if (owner, name) == ("ceo", "brief") else []


def timeline(found: list[tuple[int, JsonObject]]) -> list[tuple[int, datetime]]:
    return StorePlaybookTimelines(History(found)).timeline("ceo", "brief")


def test_it_is_a_timeline_source() -> None:
    assert isinstance(StorePlaybookTimelines(History([])), PlaybookTimelines)


@RED
def test_each_version_is_paired_with_the_time_it_was_revised() -> None:
    assert timeline([(1, {"revised": T1.isoformat()}), (2, {"revised": T2.isoformat()})]) == [(1, T1), (2, T2)]


@RED
def test_the_versions_come_oldest_first_whatever_order_the_store_gives() -> None:
    assert timeline([(2, {"revised": T2.isoformat()}), (1, {"revised": T1.isoformat()})]) == [(1, T1), (2, T2)]


@RED
def test_a_version_without_a_readable_time_is_left_out() -> None:
    assert timeline([(1, {}), (2, {"revised": "yesterday"}), (3, {"revised": ""}), (4, {"revised": T2.isoformat()})]) == [(4, T2)]


@RED
def test_version_zero_is_not_a_version() -> None:
    assert timeline([(0, {"revised": T1.isoformat()})]) == []


@RED
def test_a_time_read_by_yaml_is_accepted() -> None:
    assert timeline([(1, {"revised": T1})]) == [(1, T1)]


@RED
def test_another_service_has_no_timeline() -> None:
    assert StorePlaybookTimelines(History([(1, {"revised": T1.isoformat()})])).timeline("ceo", "other") == []
