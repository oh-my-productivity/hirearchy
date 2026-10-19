"""Helpers shared by the tests of ``services`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

import pytest
from _pytest.mark import ParameterSet

from orgmcp.kernel import Message
from orgmcp.services.testing import ServicesWorld

WORKERS = ("ceo", "ceo/eng", "ceo/qa", "ops")
LEADS = ("ceo",)

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


RED = pytest.mark.xfail(strict=True, reason="red: C-services")
PENDING: set[str] = {'hints_memory', 'normalizer', 'fs_rework', 'fs_world', 'memory_world', 'memory_rework', 'fs_store', 'hints_fs'}  # implementations that are not green yet


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The implementations a contract suite iterates over, ``IMPLEMENTATIONS[<protocol>]`` (those that are not green yet are expected to fail)."""
    return [pytest.param(f, id=f.__name__, marks=RED if f.__name__ in PENDING else ()) for f in factories]


def populated(world: ServicesWorld) -> ServicesWorld:
    """``world`` with ``ceo`` and ``ops`` (who can hire), and ``ceo/eng`` and ``ceo/qa``."""
    for addr in ("ceo", "ops"):
        world.d.agent(addr, True)
    for addr in ("ceo/eng", "ceo/qa"):
        world.d.agent(addr, False)
    return world


def make(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    """The fixture body of the suites: the populated world of one implementation."""
    return populated(cast(Callable[[Path], ServicesWorld], request.param)(tmp_path))


def define(w: ServicesWorld, owner: str = "ceo", name: str = "weekly-brief", actor: str = "root", **over: Any) -> str:
    """The client defines the service ``name`` of ``owner`` (the brief of the tests unless ``over`` changes it)."""
    given = {**BRIEF, **over}
    return w.commands.define_service(actor, owner, name, **given)


def amend(w: ServicesWorld, owner: str = "ceo", name: str = "weekly-brief", actor: str = "root", **over: Any) -> str:
    """The client amends the service: only what ``over`` names changes."""
    return w.commands.define_service(actor, owner, name, **over)


def grant(w: ServicesWorld, to: str, runs: int) -> Message:
    """A note from root that carries ``runs`` runs, delivered whatever the rules say."""
    return w.d.post(Message(sender="root", to=to, type="note", body="runs for you", title="grant", budget=runs))


def answer(w: ServicesWorld, task: Message, status: str = "done", body: str = "Delivered.") -> Message:
    """The owner of ``task`` answers it with a result of ``status`` (delivered straight)."""
    return w.d.post(Message(sender=task.to, to=task.sender, type="result", status=status, reply_to=task.id, body=body, title="Result"))


def request(w: ServicesWorld, topic: str = "ai", actor: str = "root", **kw: Any) -> Message:
    """``actor`` asks for ``weekly-brief`` with the topic ``topic``."""
    return w.commands.request(actor, "weekly-brief", {"topic": topic}, **kw)
