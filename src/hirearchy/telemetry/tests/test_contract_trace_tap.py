"""Contract of ``TraceTap`` (the kernel's port) for the real tap and the recording one."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import TraceTap
from hirearchy.telemetry.testing import IMPLEMENTATIONS



@pytest.fixture(params=IMPLEMENTATIONS[TraceTap], ids=lambda factory: factory.__name__)
def tap(request: pytest.FixtureRequest, tmp_path: Path) -> TraceTap:
    made = cast(Callable[[Path], TraceTap], request.param)(tmp_path)
    assert isinstance(made, TraceTap)
    return made


def test_note_accepts_a_trace_or_none(tap: TraceTap) -> None:
    tap.note("20261018T100000000001-root-ab12")
    tap.note(None)


def test_noting_outside_a_tool_call_is_harmless_and_repeatable(tap: TraceTap) -> None:
    for _ in range(3):
        tap.note("t")
