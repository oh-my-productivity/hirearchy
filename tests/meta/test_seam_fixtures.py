"""The fixtures that replace the module-attribute patch points (``tests/testkit/fixtures.py``): a fake clock and counting ids for every runtime
opened during the test, including the ones that code under test opens itself."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hirearchy.app import Org, wiring
from hirearchy.eventlog import EVENTS_REL

FIXED = datetime(2031, 5, 6, 7, 8, 9, tzinfo=timezone.utc)


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


def test_frozen_clock_leaves_the_events_on_the_system_time_unless_asked(frozen_clock, tmp_path: Path) -> None:
    frozen_clock(FIXED)
    org = Org.init(tmp_path / "org", "mission")
    org.emit("custom.kind")
    assert str(last_event_ts(org)).startswith(str(datetime.now(timezone.utc).year))


def test_frozen_clock_can_stamp_the_events_too(frozen_clock, tmp_path: Path) -> None:
    frozen_clock(FIXED, events=True)
    org = Org.init(tmp_path / "org", "mission")
    org.emit("custom.kind")
    assert last_event_ts(org) == "2031-05-06T07:08:09.000000+00:00"


def last_event_ts(org: Org) -> object:
    lines = [json.loads(line) for f in sorted((org.root / EVENTS_REL).glob("*/*.jsonl")) for line in f.read_text(encoding="utf-8").splitlines()]
    return lines[-1]["ts"]


def test_the_seams_are_closed_after_the_test() -> None:
    assert not wiring.overrides()
