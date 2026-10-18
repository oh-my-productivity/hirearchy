"""Step A-runs only: which implementations and tests are still red while the step is being built (deleted when all are green)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

RED: frozenset[str] = frozenset({"fs_runs", "memory_runs", "caching_fs_runs"})

red = pytest.mark.xfail(strict=True, raises=NotImplementedError, reason="red: A-runs")
red_surface = pytest.mark.xfail(strict=True, reason="red: A-runs")


def impls(factories: Sequence[Callable[[Path], object]]) -> list[object]:
    """The registered implementations (``IMPLEMENTATIONS[protocol]``) as pytest params; those in ``RED`` are strict xfails."""
    return [pytest.param(factory, id=factory.__name__, marks=red if factory.__name__ in RED else ()) for factory in factories]
