"""The organization with every flag in it (``_scenario``), built once per test with a clock that only moves when told."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hirearchy.health import HealthAnalyzer
from hirearchy.health.testing import IMPLEMENTATIONS, HealthWorld

from . import _scenario
from ._support import implementations


@pytest.fixture
def scenario(tmp_path: Path, process_overrides: Any) -> Any:
    """The ``Org`` facade of ``_scenario.build``; the clock and the ids of the runtimes are fixed for the length of the test."""
    clock = _scenario.install(process_overrides)
    return _scenario.build(tmp_path, clock)


@pytest.fixture(params=implementations(IMPLEMENTATIONS[HealthAnalyzer]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> HealthWorld:
    """An organization of ``ceo`` and ``ceo/eng`` (both hired at the origin of time, 10 runs left each), over disk and over memory."""
    made: HealthWorld = request.param(tmp_path)
    assert isinstance(made.analyzer, HealthAnalyzer)
    made.agent("ceo", 0)
    made.agent("ceo/eng", 0)
    made.set_budget("ceo", 10)
    made.set_budget("ceo/eng", 10)  # budget left, so that out_of_budget does not mix into the other flags
    return made
