"""Helpers shared by the tests of ``daemon`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar, cast

import pytest
from _pytest.mark.structures import ParameterSet

W = TypeVar("W")


def worlds(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """One parameter per implementation (the worlds of ``testing.IMPLEMENTATIONS`` for a port)."""
    return [pytest.param(factory, id=factory.__name__) for factory in factories]


def build(request: pytest.FixtureRequest, tmp_path: Path, kind: type[W]) -> W:
    """The fixture body of a contract suite: the world of one implementation (a ``kind``)."""
    return cast(Callable[[Path], W], request.param)(tmp_path)
