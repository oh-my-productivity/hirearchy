"""Helpers shared by the tests of ``health`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet

from orgmcp.health.testing import HealthWorld, at

RED = pytest.mark.xfail(strict=True, reason="red: C-health", raises=NotImplementedError)  # removed from each file by the step that makes it pass


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The factories of one port as test parameters, named by the factory."""
    return [pytest.param(f, id=f.__name__) for f in factories]


__all__ = ["RED", "answer", "at", "give", "implementations", "runs"]


def give(w: HealthWorld, to: str = "ceo/eng", when: float = 10, *, budget: int = 5, sender: str = "root", revises: str | None = None,
         service: str | None = None, title: str = "Job") -> str:
    """A task sent at ``when``, which the assignee has read (nothing unread is left); returns its id."""
    task = w.send(sender, to, "task", when, title=title, budget=budget, revises=revises, service=service)
    w.read(to)
    return task.id


def answer(w: HealthWorld, task_id: str, status: str, when: float, *, sender: str = "ceo/eng", to: str = "root") -> str:
    """The result of a task, sent by its assignee; returns its id."""
    return w.send(sender, to, "result", when, status=status, reply_to=task_id).id


def runs(w: HealthWorld, addr: str, n: int, first: float = 100, footer: str = "") -> None:
    """``n`` runs of 50 s, one every 100 s from ``first``."""
    for i in range(n):
        w.run(addr, first + i * 100, first + i * 100 + 50, footer)
