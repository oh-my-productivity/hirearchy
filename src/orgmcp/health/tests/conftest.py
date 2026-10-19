"""The organization with every flag in it (``_scenario``), built once per test with a clock that only moves when told."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from . import _scenario


@pytest.fixture
def scenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The legacy ``Org`` of ``_scenario.build``; ``core.utcnow`` and ``core.secrets`` are patched for the length of the test."""
    clock = _scenario.install(monkeypatch)
    return _scenario.build(tmp_path, clock)
