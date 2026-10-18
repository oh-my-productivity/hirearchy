"""The legs of the contract suites whose implementation is not written yet (RED -> GREEN, step A-agents). Deleted when the last one is."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

STILL_RED: frozenset[str] = frozenset({"fs_agents", "caching_agents", "lenient_agents"})


def params(factories: Sequence[Callable[[Path], object]]) -> list[object]:
    """``pytest.param`` for each implementation: a strict xfail while the implementation is not there."""
    return [
        pytest.param(f, id=f.__name__, marks=[pytest.mark.xfail(strict=True, reason="red: A-agents")] if f.__name__ in STILL_RED else [])
        for f in factories
    ]
