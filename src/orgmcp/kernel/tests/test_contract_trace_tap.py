"""Contract of ``TraceTap``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import TraceTap
from orgmcp.kernel.testing import IMPLEMENTATIONS


@pytest.fixture(params=IMPLEMENTATIONS[TraceTap], ids=lambda factory: factory.__name__)
def tap(request: pytest.FixtureRequest, tmp_path: Path) -> TraceTap:
    made = cast(Callable[[Path], TraceTap], request.param)(tmp_path)
    assert isinstance(made, TraceTap)
    return made


def test_note_accepts_a_trace_or_none(tap: TraceTap) -> None:
    tap.note("20261018T100000000001-root-ab12")
    tap.note(None)
