"""Helpers shared by the tests of ``budget`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.budget.testing import BudgetWorld
from hirearchy.kernel import Message

HIRERS = ("ceo", "ceo/ops")
WORKERS = ("ceo/eng", "ceo/qa", "ceo/ops/dev")


def populated(world: BudgetWorld) -> BudgetWorld:
    """``world`` with ``ceo`` and ``ceo/ops`` (who can hire), and ``ceo/eng``, ``ceo/qa`` and ``ceo/ops/dev``."""
    for addr in HIRERS:
        world.agent(addr, True)
    for addr in WORKERS:
        world.agent(addr, False)
    return world


def make(request: pytest.FixtureRequest, tmp_path: Path) -> BudgetWorld:
    """The fixture body of the contract suites: the populated world of one implementation."""
    return populated(cast(Callable[[Path], BudgetWorld], request.param)(tmp_path))


def grant(world: BudgetWorld, sender: str, to: str, runs: int) -> Message:
    """A note that carries ``runs``."""
    return world.post(Message(sender=sender, to=to, type="note", body="runs for you", title="grant", budget=runs))


def assign(world: BudgetWorld, sender: str, to: str, runs: int = 0, revises: str | None = None) -> Message:
    """A task that carries ``runs`` (``revises``: it sends the earlier task back for rework)."""
    return world.post(Message(sender=sender, to=to, type="task", body="goal", title="Work", budget=runs, revises=revises))


def verdict(world: BudgetWorld, task: Message, kind: str = "accept") -> Message:
    """The assigner's quiet verdict note on the result of ``task``."""
    return world.post(Message(sender=task.sender, to=task.to, type="note", body="as is", title="verdict", feedback=kind, reply_to=task.id))


def report(world: BudgetWorld, task: Message, status: str = "done", runs: int = 0) -> Message:
    """The result of ``task`` from its assignee to its sender; ``runs`` travel up with it."""
    return world.post(Message(
        sender=task.to, to=task.sender, type="result", body="done", title=task.title, reply_to=task.id, status=status, budget=runs,
    ))
