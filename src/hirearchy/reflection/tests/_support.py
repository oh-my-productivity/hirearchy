"""Helpers shared by the tests of ``reflection`` (no test lives here): the people of the organization and the stories the tests tell in it."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

import pytest
from _pytest.mark import ParameterSet

from hirearchy.kernel import Message
from hirearchy.reflection.testing import ReflectionWorld

SERVICE = "weekly-brief"
BRIEF: dict[str, object] = dict(
    description="A one-page brief on the past week's news about a topic.",
    inputs=[
        {"name": "topic", "description": "what the brief is about", "required": True},
        {"name": "week", "description": "ISO week; default the current one", "required": False},
    ],
    acceptance=["At most 600 words", "Every factual claim has a source URL"],
    deliverable={"description": "one markdown file", "format": "markdown", "max_words": 600},
    budget=10,
)
STEPS = "## Steps\n1. Search.\n2. Write.\n3. Check every claim."


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The implementations a contract suite iterates over, ``IMPLEMENTATIONS[<protocol>]``, with their names as ids."""
    return [pytest.param(f, id=f.__name__) for f in factories]


def populated(world: ReflectionWorld) -> ReflectionWorld:
    """``world`` with ``ceo`` and ``ops`` (who can hire), and ``ceo/eng`` and ``ceo/qa``."""
    for addr in ("ceo", "ops"):
        world.s.d.agent(addr, True)
    for addr in ("ceo/eng", "ceo/qa"):
        world.s.d.agent(addr, False)
    return world


def make(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    """The fixture body of the suites: the populated world of one implementation."""
    return populated(cast(Callable[[Path], ReflectionWorld], request.param)(tmp_path))


def define(w: ReflectionWorld, owner: str = "ceo", name: str = SERVICE, **over: Any) -> str:
    """The client defines the service ``name`` of ``owner`` (the brief of the tests unless ``over`` changes it)."""
    return w.s.commands.define_service("root", owner, name, **{**BRIEF, **over})


def ask(w: ReflectionWorld, topic: str = "ai", **kw: Any) -> Message:
    """The client asks for ``weekly-brief`` with the topic ``topic`` (``revises=...`` sends an earlier request back)."""
    return w.s.commands.request("root", SERVICE, {"topic": topic}, **kw)


def deliver(w: ReflectionWorld, task: Message, status: str = "done", runs: int = 1, lessons: str = "") -> Message:
    """The owner of ``task`` makes ``runs`` runs and answers it; ``lessons`` become the ``## Lessons`` section of the result."""
    for _ in range(runs):
        w.use_run(task.to)
    body = "Delivered." + (f"\n\n## Lessons\n{lessons}" if lessons else "")
    return w.s.d.post(Message(sender=task.to, to=task.sender, type="result", status=status, reply_to=task.id, body=body, title="Result"))


def rate(w: ReflectionWorld, task: Message, verdict: str, note: str = "") -> Message:
    """The client's verdict on a delivered request."""
    return w.s.commands.feedback("root", task.id, verdict, note)


def revise(w: ReflectionWorld, content: str = STEPS, reason: str = "first", owner: str = "ceo") -> int:
    """The owner writes the next version of the playbook; time moves a second first, so that it lies between the cases around it."""
    w.s.d.clock.advance(1)
    return w.s.commands.revise_playbook(owner, SERVICE, content, reason)


def rework(w: ReflectionWorld, task: Message, **kw: Any) -> Message:
    """The client sends ``task`` back (the user asked for it: ``source="human"``, unless ``kw`` says otherwise)."""
    return w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=task.id, **{"source": "human", **kw})


def read_inbox(w: ReflectionWorld, addr: str = "ceo") -> None:
    """The owner has seen everything in its inbox: the next batch holds only what arrives from now on."""
    w.s.d.begin_run(addr)
    w.s.d.end_run(addr)
