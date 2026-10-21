"""Contract of ``Clock``: every registered implementation (the system clock and the fake) passes the same tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import Clock
from hirearchy.kernel.testing import IMPLEMENTATIONS


@pytest.fixture(params=IMPLEMENTATIONS[Clock], ids=lambda factory: factory.__name__)
def clock(request: pytest.FixtureRequest, tmp_path: Path) -> Clock:
    made = cast(Callable[[Path], Clock], request.param)(tmp_path)
    assert isinstance(made, Clock)
    return made


def test_now_is_aware_utc(clock: Clock) -> None:
    now = clock.now()
    assert now.tzinfo is not None and now.utcoffset() == timedelta(0)


def test_now_never_goes_backwards(clock: Clock) -> None:
    readings = [clock.now() for _ in range(50)]
    assert readings == sorted(readings)


def test_time_is_the_epoch_seconds_of_now(clock: Clock) -> None:
    before = clock.now().timestamp()
    epoch = clock.time()
    after = clock.now().timestamp()
    assert before - 1.0 <= epoch <= after + 1.0


def test_monotonic_never_goes_backwards(clock: Clock) -> None:
    readings = [clock.monotonic() for _ in range(50)]
    assert readings == sorted(readings)


def test_sleep_moves_both_clocks_forward(clock: Clock) -> None:
    mono, now = clock.monotonic(), clock.now()
    clock.sleep(0.05)
    assert clock.monotonic() - mono >= 0.04
    assert (clock.now() - now).total_seconds() >= 0.04


def test_sleeping_zero_seconds_returns(clock: Clock) -> None:
    clock.sleep(0)
