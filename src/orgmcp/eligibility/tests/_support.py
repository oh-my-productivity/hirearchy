"""Helpers shared by the tests of ``eligibility`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The factories of one port as test parameters, named by the factory."""
    return [pytest.param(f, id=f.__name__) for f in factories]
