"""Helpers shared by the tests of ``eligibility`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet

RED = pytest.mark.xfail(strict=True, reason="red: B-eligibility")
PASSING: frozenset[str] = frozenset()  # the implementations that already pass their contract suite; the others are red


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The factories of one port as test parameters: the ones not in ``PASSING`` are expected to fail for now."""
    return [pytest.param(f, id=f.__name__, marks=[] if f.__name__ in PASSING else [RED]) for f in factories]
