"""The organization of ``_scenario``, built once per test with a clock that only moves when told."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from . import _scenario


@pytest.fixture
def scenario(tmp_path: Path, process_overrides: Any) -> Any:
    """The legacy ``Org`` of ``_scenario.build``; the clock and the ids of the runtimes are fixed for the length of the test."""
    clock = _scenario.install(process_overrides)
    return _scenario.build(tmp_path, clock)
