"""The fixtures that replace the module-attribute patch points (``tests/testkit/fixtures.py``): a fake clock and counting ids for every runtime
opened during the test, including the ones that code under test opens itself."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orgmcp.app import Org, wiring

FIXED = datetime(2031, 5, 6, 7, 8, 9, tzinfo=timezone.utc)


pytestmark = pytest.mark.xfail(strict=True, reason="red: E2-compat")

def test_frozen_clock_serves_a_datetime(frozen_clock, tmp_path: Path) -> None:
    frozen_clock(FIXED)
    assert wiring.open_runtime(tmp_path).clock.now() == FIXED


def test_frozen_clock_serves_a_function_and_returns_it(frozen_clock, tmp_path: Path) -> None:
    ticks = iter(range(100))
    clock = frozen_clock(lambda: FIXED + timedelta(seconds=next(ticks)))
    runtime = wiring.open_runtime(tmp_path)
    assert (runtime.clock.now(), runtime.clock.now()) == (FIXED, FIXED + timedelta(seconds=1)) and callable(clock)


def test_counter_ids_make_the_ids_of_an_org_opened_by_the_code_under_test_stable(frozen_clock, counter_ids, tmp_path: Path) -> None:
    frozen_clock(FIXED)
    counter_ids(per_length=True)
    org = Org.init(tmp_path / "org", "mission")
    assert [org.new_id("ceo"), org.new_id("ceo")] == ["20310506T070809000000-ceo-0000", "20310506T070809000000-ceo-0001"]


def test_counter_ids_can_count_per_length_and_expose_the_counts(counter_ids, tmp_path: Path) -> None:
    tokens = counter_ids(per_length=True)
    wiring.open_runtime(tmp_path).ids.message_id("a")
    assert tokens.counts == {2: 1}


def test_the_seams_are_closed_after_the_test() -> None:
    assert not wiring.overrides()
