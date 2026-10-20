"""Helpers shared by the tests of ``hierarchy`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.hierarchy.testing import HierarchyWorld
from orgmcp.kernel import Message

BOSS = {"role": "Chief", "tools": [], "can_hire": True, "max_children": 2, "hired_by": "root"}  # the charter of ``ceo``
WORKER = {"role": "Worker", "tools": [], "can_hire": False, "max_children": 5, "hired_by": "ceo"}


def populated(world: HierarchyWorld) -> HierarchyWorld:
    """``world`` with ``ceo`` (who can hire, up to two reports) and its report ``ceo/eng``."""
    world.agent("ceo", BOSS)
    world.agent("ceo/eng", WORKER)
    return world


def make(request: pytest.FixtureRequest, tmp_path: Path) -> HierarchyWorld:
    """The fixture body of the contract suites: the populated world of one implementation."""
    return populated(cast(Callable[[Path], HierarchyWorld], request.param)(tmp_path))


def outside(world: HierarchyWorld, name: str) -> str:
    """The path of a folder that lies outside the organization (inputs and workspaces are such folders)."""
    return str(world.root.parent / "outside" / name)


def grant(world: HierarchyWorld, sender: str, to: str, runs: int) -> Message:
    """A note that carries ``runs``."""
    return world.post(Message(sender=sender, to=to, type="note", body="runs for you", title="grant", budget=runs))


def assign(world: HierarchyWorld, sender: str, to: str, runs: int = 0, title: str = "Work") -> Message:
    """A task that carries ``runs``."""
    return world.post(Message(sender=sender, to=to, type="task", body="goal", title=title, budget=runs))
