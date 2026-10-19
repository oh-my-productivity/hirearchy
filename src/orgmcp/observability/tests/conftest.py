"""The organizations of ``_scenario``, built once per test with a clock that only moves when told and ids that are the same in every run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from . import _scenario


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Any:
    return _scenario.install(monkeypatch)


@pytest.fixture
def built(tmp_path: Path, clock: Any) -> Any:
    """The story, extended: a rework, a service task, a retired agent's run, lifecycle events, faults (events written by hand, emission off)."""
    made = _scenario.story(tmp_path, clock)
    _scenario.extend(made)
    return made
