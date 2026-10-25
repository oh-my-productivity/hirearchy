"""``HealthFailCounts`` and ``ReadableOrgConfig``: the two adapters the quality view's ports are made of (design 12.5)."""

from __future__ import annotations

import pytest

from hirearchy.app._fail_counts import HealthFailCounts
from hirearchy.app._readable_config import ReadableOrgConfig
from hirearchy.health._ports import EscapeCounter, EscapeCounts
from hirearchy.kernel import OrgError
from hirearchy.progress._ports import ConfigSource, FailCounts
from hirearchy.settings.testing import MemoryOrgSettings


class CannedCounts(EscapeCounter):
    def __init__(self) -> None:
        self.asked: list[str] = []

    def counts(self, addr: str) -> EscapeCounts:
        self.asked.append(addr)
        return EscapeCounts(escapes=4, judged=9, rechecks=2, rework_runs=3)


def test_fail_counts_are_the_rechecks_and_the_rework_runs_of_the_health_counter() -> None:
    counter = CannedCounts()
    fails = HealthFailCounts(counter)
    assert isinstance(fails, FailCounts)
    assert fails.fails("lead/checker") == (2, 3) and counter.asked == ["lead/checker"]


def test_the_config_is_the_readable_config_of_org_md() -> None:
    source = ReadableOrgConfig(MemoryOrgSettings("---\nquality:\n  min_judged: 5\n---\nRules.\n"))
    assert isinstance(source, ConfigSource)
    assert source.config()["quality"] == {"min_judged": 5}


def test_an_org_md_that_does_not_parse_is_an_org_error_that_names_it() -> None:
    with pytest.raises(OrgError, match="ORG.md cannot be read"):
        ReadableOrgConfig(MemoryOrgSettings("---\nkey: [unclosed\n---\n")).config()
