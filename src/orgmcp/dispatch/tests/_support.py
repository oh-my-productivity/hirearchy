"""Helpers shared by the tests of ``dispatch`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

import pytest
from _pytest.mark import ParameterSet

from orgmcp.dispatch.testing import DispatchWorld
from orgmcp.kernel import Message

HIRERS = ("ceo", "ceo/ops")
WORKERS = ("ceo/eng", "ceo/qa", "ceo/ops/dev")



def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The implementations a contract suite iterates over, ``IMPLEMENTATIONS[<protocol>]``, with their names as ids."""
    return [pytest.param(f, id=f.__name__) for f in factories]


def populated(world: DispatchWorld) -> DispatchWorld:
    """``world`` with ``ceo`` and ``ceo/ops`` (who can hire), and ``ceo/eng``, ``ceo/qa`` and ``ceo/ops/dev``."""
    for addr in HIRERS:
        world.agent(addr, True)
    for addr in WORKERS:
        world.agent(addr, False)
    return world


def make(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    """The fixture body of the suites: the populated world of one implementation."""
    return populated(cast(Callable[[Path], DispatchWorld], request.param)(tmp_path))


def grant(world: DispatchWorld, sender: str, to: str, runs: int) -> Message:
    """A note that carries ``runs``, delivered whatever the rules say."""
    return world.post(Message(sender=sender, to=to, type="note", body="runs for you", title="grant", budget=runs))


def assigned(world: DispatchWorld, to: str = "ceo", runs: int = 6, **fields: object) -> Message:
    """A task from root to ``to`` with ``runs`` runs, read by ``to`` in a run (so that it is not waiting for one). ``fields`` set more of the task."""
    task = Message(sender="root", to=to, type="task", body="## Goal\nDo it.", title="Work", budget=runs)
    for name, value in fields.items():
        setattr(task, name, value)
    world.post(task)
    world.begin_run(to)
    world.use_run(to)
    return task
