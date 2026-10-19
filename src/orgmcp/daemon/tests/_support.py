"""Helpers shared by the tests of ``daemon`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar, cast

import pytest
from _pytest.mark.structures import ParameterSet

W = TypeVar("W")

RED = "red: C-daemon"
PENDING: frozenset[str] = frozenset(
    {
        "pidfile_status_world", "real_status_world", "memory_status_world",
        "pidfile_control_world", "real_control_world", "memory_control_world",
        "pidfile_lock_world", "real_lock_world", "memory_lock_world",
        "file_exit_marker_world", "memory_exit_marker_world",
        "venv_command_world", "fake_command_world",
    }
)  # the worlds whose classes are not written yet: their contract tests are expected to fail


def worlds(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """One parameter per implementation (the worlds of ``testing.IMPLEMENTATIONS`` for a port)."""
    return [
        pytest.param(factory, id=factory.__name__, marks=[pytest.mark.xfail(strict=True, reason=RED)] if factory.__name__ in PENDING else [])
        for factory in factories
    ]


def build(request: pytest.FixtureRequest, tmp_path: Path, kind: type[W]) -> W:
    """The fixture body of a contract suite: the world of one implementation (a ``kind``)."""
    return cast(Callable[[Path], W], request.param)(tmp_path)
