"""Helpers shared by the tests of ``health`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet

from hirearchy.health.testing import HealthWorld, at

__all__ = [
    "AUTHOR", "CHECKER", "OWNER", "SERVICE", "Delivery", "answer", "at", "deliver", "give", "implementations", "request", "runs", "verdict",
]


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The factories of one port as test parameters, named by the factory."""
    return [pytest.param(f, id=f.__name__) for f in factories]


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


# ------------------------------------------------------------------------------------------------------------------------ a service delivery
# The organization is ``root -> ceo`` (the owner of the service) ``-> ceo/eng`` (an author) and ``ceo/chk`` (a checker; the world adds it).

OWNER, AUTHOR, CHECKER = "ceo", "ceo/eng", "ceo/chk"
SERVICE = "weekly-brief"


@dataclass
class Delivery:
    request: str  # T
    done: str  # D
    author_task: str | None = None
    check_task: str | None = None


def request(w: HealthWorld, when: float, *, source: str | None = None, sender: str = "root", service: str | None = SERVICE, revises: str | None = None) -> str:
    """``sender`` asks the owner for the service at ``when`` (the owner has read it); returns the task id."""
    task = w.send(sender, OWNER, "task", when, service=service, source=source, revises=revises)
    w.read(OWNER)
    return task.id


def deliver(w: HealthWorld, when: float, *, team: bool = True, source: str | None = None, check_first: bool = False) -> Delivery:
    """The owner gets a request at ``when``; with ``team`` its author drafts and its checker passes it; then it reports ``done`` (all within 9 s)."""
    t = request(w, when, source=source)
    author = check = None
    if team:
        author = w.send(OWNER, AUTHOR, "task", when + 1).id
        w.send(AUTHOR, OWNER, "result", when + 2, status="done", reply_to=author)
        check = w.send(OWNER, CHECKER, "task", when + 3).id
        w.send(CHECKER, OWNER, "result", when + 4, status="done", reply_to=check)
    d = w.send(OWNER, "root", "result", when + 6, status="done", reply_to=t).id
    return Delivery(t, d, author, check)


def verdict(w: HealthWorld, task_id: str, when: float, kind: str = "reject", *, source: str | None = "human", sender: str = "root") -> str:
    """The client's verdict on a delivered task."""
    return w.send(sender, OWNER, "note", when, reply_to=task_id, feedback=kind, source=source).id
