"""Helpers shared by the tests of ``blueprint`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar, cast

import pytest
from _pytest.mark import ParameterSet

from orgmcp.blueprint.api import Role

RED = pytest.mark.xfail(strict=True, reason="red: C-blueprint-1")
PENDING: set[str] = {'packaged_roles', 'memory_roles', 'loader_over_memory', 'loader_over_disk', 'validator_over_packaged_roles', 'validator_over_memory_roles'}  # contract-suite implementations that are not green yet (expected to fail)
T = TypeVar("T")


def make(request: pytest.FixtureRequest, tmp_path: Path, kind: type[T]) -> T:
    """The fixture body of every contract suite: the harness of one registered factory."""
    made = cast(Callable[[Path], object], request.param)(tmp_path)
    assert isinstance(made, kind)
    return made


def role(name: str = "writer", **over: object) -> Role:
    values: dict[str, object] = {
        "name": name, "title": "Writer", "kind": "author", "tier": "cheap", "tools": ("read", "write"), "base_runs": 2,
        "summary": "Writes the report.", "body": "You write the report.\n\nKeep it short.",
    }
    values.update(over)
    return Role(**values)  # type: ignore[arg-type]


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The implementations a contract suite iterates over, ``IMPLEMENTATIONS[<protocol>]`` (those that are not green yet are expected to fail)."""
    return [pytest.param(f, id=f.__name__, marks=RED if f.__name__ in PENDING else ()) for f in factories]
