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


def define(w: ReflectionWorld, owner: str = "ceo", name: str = SERVICE, actor: str = "root", **over: Any) -> str:
    """``actor``, the client, defines the service ``name`` of ``owner`` (the brief of the tests unless ``over`` changes it)."""
    return w.s.commands.define_service(actor, owner, name, **{**BRIEF, **over})


def ask(w: ReflectionWorld, topic: str = "ai", **kw: Any) -> Message:
    """The client asks for ``weekly-brief`` with the topic ``topic`` (``revises=...`` sends an earlier request back)."""
    return w.s.commands.request("root", SERVICE, {"topic": topic}, **kw)


def deliver(w: ReflectionWorld, task: Message, status: str = "done", runs: int = 1, lessons: str = "", budget: int = 0) -> Message:
    """The owner of ``task`` makes ``runs`` runs and answers it; ``lessons`` become the ``## Lessons`` section of the result; ``budget`` is the
    runs the result carries back to the client."""
    for _ in range(runs):
        w.use_run(task.to)
    body = "Delivered." + (f"\n\n## Lessons\n{lessons}" if lessons else "")
    return w.s.d.post(Message(
        sender=task.to, to=task.sender, type="result", status=status, reply_to=task.id, body=body, title="Result", budget=budget,
    ))


def rate(w: ReflectionWorld, task: Message, verdict: str, note: str = "", **kw: Any) -> Message:
    """The client's verdict on a delivered request (the user's own judgement: ``source="human"``, unless ``kw`` says otherwise)."""
    return w.s.commands.feedback("root", task.id, verdict, note, **{"source": "human", **kw})


def note_on(w: ReflectionWorld, task: Message, *, verdict: str | None = None, reply_to: str | None = None, **kw: Any) -> Message:
    """A note from root delivered straight, as the sender would stamp it: a verdict on ``task`` (``verdict``), or a link note replying to
    ``reply_to`` (``criterion=...``). ``source``, ``criterion`` and ``body`` go in ``kw``."""
    return w.s.d.post(Message(
        sender="root", to=task.to, type="note", title="note", body=kw.pop("body", "the client's words"), feedback=verdict,
        reply_to=reply_to or (task.id if verdict else None), **kw,
    ))


def nested(w: ReflectionWorld) -> Message:
    """An agent is the client: ``ceo`` defines a service for its report ``ceo/eng`` and asks for it; the delivered request is returned."""
    grant = Message(sender="root", to="ceo", type="note", body="runs for you", title="grant", budget=20)
    w.s.d.post(grant)
    define(w, "ceo/eng", "inner", actor="ceo")
    task = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    return deliver(w, task)


def revise(w: ReflectionWorld, content: str = STEPS, reason: str = "first", owner: str = "ceo") -> int:
    """The owner writes the next version of the playbook (the world's gate admits it: ``evidence=("R1",)``); time moves a second first, so
    that it lies between the cases around it."""
    w.s.d.clock.advance(1)
    return w.s.commands.revise_playbook(owner, SERVICE, content, reason, evidence=("R1",))


def rework(w: ReflectionWorld, task: Message, **kw: Any) -> Message:
    """The client sends ``task`` back (the user asked for it: ``source="human"``, unless ``kw`` says otherwise)."""
    return w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=task.id, **{"source": "human", **kw})


def read_inbox(w: ReflectionWorld, addr: str = "ceo") -> None:
    """The owner has seen everything in its inbox: the next batch holds only what arrives from now on."""
    w.s.d.begin_run(addr)
    w.s.d.end_run(addr)


def amend_legacy(w: ReflectionWorld, add_acceptance: Sequence[str] = (), remove_acceptance: Sequence[str] = (), owner: str = "ceo") -> None:
    """Root's amendment written the way a contract version was before 0a.2: criteria added or removed, no answer and no words in the frontmatter (a
    legacy version: the 0a.1 rule applies to its criteria, so a human ``confirms`` link makes an added one eligible). Today's ``define_service``
    records the user's words, so a test of the legacy rule writes the version itself."""
    found = w.s.store.read_contract(owner, SERVICE)
    assert found is not None
    meta, body = found
    version = int(str(meta["version"])) + 1
    kept = [t for t in meta["acceptance"] if t not in remove_acceptance]  # type: ignore[attr-defined]
    for key in ("answers", "about", "words", "initiated"):
        meta.pop(key, None)
    w.s.store.write_contract(
        owner, SERVICE, {**meta, "version": version, "acceptance": [*kept, *add_acceptance], "defined_by": "root",
                         "defined": w.s.d.clock.now().isoformat(timespec="microseconds")}, body, version - 1,
    )


def s1_t6(w: ReflectionWorld) -> Message:
    """E5 s1 at T6 (contract 12): f07a (12 handed down, 5 runs, 7 returned), aae2 human (12, 5, 7), 963a relayed (6, 5, 1); the relayed task is returned."""
    first = ask(w, "s1")
    deliver(w, first, runs=5, budget=7)
    human = rework(w, first, budget=12)
    deliver(w, human, runs=5, budget=7)
    relayed = rework(w, human, source="relayed", budget=6)
    deliver(w, relayed, runs=5, budget=1)
    return relayed

