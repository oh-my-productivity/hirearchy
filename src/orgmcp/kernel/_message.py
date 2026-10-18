"""The message: one markdown file with YAML frontmatter, as a value."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Self, runtime_checkable

from ._ports import JsonObject

MESSAGE_TYPES = ("task", "result", "note")
RESULT_STATUSES = ("done", "failed", "blocked")
RENDER_BODY_CHARS = 8000  # longer bodies are cut when shown to an agent (prompt, inbox tool); the file has the rest


@runtime_checkable
class MessageView(Protocol):
    """What a message can show of itself: its frontmatter, its file text, the text an agent is shown."""

    def meta(self) -> JsonObject:
        """The frontmatter of the message's file."""
        ...

    def to_text(self) -> str:
        """The text of the message's file."""
        ...

    def cut_body(self, limit: int = RENDER_BODY_CHARS, where: str | None = None) -> str:
        """The body, cut to ``limit`` characters with a pointer to the file for the rest."""
        ...

    def render(self, limit: int = RENDER_BODY_CHARS) -> str:
        """The message as shown to an agent."""
        ...


@dataclass
class Message(MessageView):
    sender: str
    to: str
    type: str
    body: str
    title: str = ""
    reply_to: str | None = None
    status: str | None = None
    budget: int = 0
    hops: int = 0
    wake: bool = True  # False: held in the inbox without waking the agent; part of its next real run's batch
    revises: str | None = None  # a task sent back for rework: the earlier task it revises
    supersedes: str | None = None  # a result that replaces an earlier ``blocked`` result of the same task
    service: str | None = None  # a task that is a request for this service (and its rework tasks)
    contract: int | None = None  # version of the service contract the request was built from
    playbook: int | None = None  # version of the playbook current when the request was sent (0 = none)
    feedback: str | None = None  # "accept" | "reject" on the note that carries the client's verdict
    trace: str | None = None  # id of the root task (request) this message belongs to; stamped by the runtime at send time
    id: str = ""
    created: str = ""
    path: Path | None = field(default=None, compare=False, repr=False)

    def meta(self) -> JsonObject:
        raise NotImplementedError("red: K1")

    def to_text(self) -> str:
        raise NotImplementedError("red: K1")

    @classmethod
    def parse(cls, text: str, path: Path | None = None) -> Self:
        """A message from the text of its file (pure: no file access)."""
        raise NotImplementedError("red: K1")

    @classmethod
    def from_parts(cls, meta: JsonObject, body: str, path: Path | None = None) -> Self:
        """A message from an already split file: its frontmatter and its body."""
        raise NotImplementedError("red: K1")

    def cut_body(self, limit: int = RENDER_BODY_CHARS, where: str | None = None) -> str:
        raise NotImplementedError("red: K1")

    def render(self, limit: int = RENDER_BODY_CHARS) -> str:
        raise NotImplementedError("red: K1")


def latest_results(results: Iterable[Message]) -> dict[str, Message]:
    """The latest result per task id (``reply_to``): the task's current outcome."""
    raise NotImplementedError("red: K1")
