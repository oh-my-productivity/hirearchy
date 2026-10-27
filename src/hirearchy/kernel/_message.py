"""The message: one markdown file with YAML frontmatter, as a value."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Self, SupportsInt, cast, runtime_checkable

from ._address import ROOT, RUNTIME
from ._frontmatter import join_frontmatter, split_frontmatter
from ._ports import JsonObject

MESSAGE_TYPES = ("task", "result", "note")
RESULT_STATUSES = ("done", "failed", "blocked")
SOURCES = ("human", "relayed")  # where a verdict, a link or a rework comes from: the user's own judgement, or the assistant's reading
RENDER_BODY_CHARS = 8000  # longer bodies are cut when shown to an agent (prompt, inbox tool); the file has the rest


def _opt_int(value: object) -> int | None:
    """An optional integer frontmatter field; anything that is not a whole number reads as absent."""
    try:
        return None if value is None or isinstance(value, bool) else int(cast("SupportsInt | str", value))
    except (TypeError, ValueError):
        return None


def _int(value: object) -> int:
    return int(cast("SupportsInt | str", value))


def _text(value: object) -> str | None:
    return str(value) if value else None


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
    source: str | None = None  # "human" | "relayed": set by root only, on a verdict, a link or a rework (see ``verdict_tier``)
    criterion: str | None = None  # ids a rejection is about, joined by ", " ("C6", "C6, R2", "none"); root only, on a verdict or a link note
    trace: str | None = None  # id of the root task (request) this message belongs to; stamped by the runtime at send time
    acknowledges: str | None = None  # "{service} {op} {item}[ {text hash}]": the parent's acknowledgement of a playbook change; set only by ``acknowledge_playbook``
    id: str = ""
    created: str = ""
    path: Path | None = field(default=None, compare=False, repr=False)

    def meta(self) -> JsonObject:
        meta: JsonObject = {
            "id": self.id,
            "from": self.sender,
            "to": self.to,
            "type": self.type,
            "title": self.title,
            "created": self.created,
            "hops": self.hops,
        }
        if not self.wake:
            meta["wake"] = False
        if self.reply_to:
            meta["reply_to"] = self.reply_to
        if self.status:
            meta["status"] = self.status
        if self.budget:
            meta["budget"] = self.budget
        if self.revises:
            meta["revises"] = self.revises
        if self.supersedes:
            meta["supersedes"] = self.supersedes
        if self.service:
            meta["service"] = self.service
        if self.contract is not None:
            meta["contract"] = self.contract
        if self.playbook is not None:
            meta["playbook"] = self.playbook
        if self.feedback:
            meta["feedback"] = self.feedback
        if self.source:
            meta["source"] = self.source
        if self.criterion:
            meta["criterion"] = self.criterion
        if self.trace:
            meta["trace"] = self.trace
        if self.acknowledges:
            meta["acknowledges"] = self.acknowledges
        return meta

    def to_text(self) -> str:
        return join_frontmatter(self.meta(), self.body)

    @classmethod
    def parse(cls, text: str, path: Path | None = None) -> Self:
        """A message from the text of its file (pure: no file access).

        Line endings are normalised first (CRLF and CR become LF), as when a file is read as text."""
        meta, body = split_frontmatter(text.replace("\r\n", "\n").replace("\r", "\n"))
        return cls.from_parts(meta, body, path)

    @classmethod
    def from_parts(cls, meta: JsonObject, body: str, path: Path | None = None) -> Self:
        """A message from an already split file: its frontmatter and its body."""
        return cls(
            sender=str(meta.get("from", "")),
            to=str(meta.get("to", "")),
            type=str(meta.get("type", "note")),
            body=body.strip(),
            title=str(meta.get("title") or ""),
            reply_to=cast("str | None", meta.get("reply_to")),
            status=cast("str | None", meta.get("status")),
            budget=_int(meta.get("budget") or 0),
            hops=_int(meta.get("hops") or 0),
            wake=meta.get("wake", True) is not False,
            revises=_text(meta.get("revises")),
            supersedes=_text(meta.get("supersedes")),
            service=_text(meta.get("service")),
            contract=_opt_int(meta.get("contract")),
            playbook=_opt_int(meta.get("playbook")),
            feedback=_text(meta.get("feedback")),
            source=_text(meta.get("source")),
            criterion=_text(meta.get("criterion")),
            trace=_text(meta.get("trace")),
            acknowledges=_text(meta.get("acknowledges")),
            id=str(meta.get("id") or (path.stem if path else "")),
            created=str(meta.get("created") or ""),
            path=path,
        )

    def cut_body(self, limit: int = RENDER_BODY_CHARS, where: str | None = None) -> str:
        """The body, cut to ``limit`` characters with a pointer to the file for the rest.

        ``where`` = path of the file relative to the org root; by default derived from the recipient's box.
        """
        body = self.body
        if limit and len(body) > limit:
            if where is None:
                where = f"{self.to}/" if self.to != ROOT else ""
                where += f"{self.path.parent.name}/{self.path.name}" if self.path else f"<box>/{self.id}.md"
            body = (
                body[:limit].rstrip()
                + f"\n\n[... message cut: {len(self.body) - limit} more of {len(self.body)} characters. "
                f"Read the rest with read(path=\"{where}\") if you need it.]"
            )
        return body

    def render(self, limit: int = RENDER_BODY_CHARS) -> str:
        """The message as shown to an agent. A body over ``limit`` characters is cut, with the path to read the rest."""
        head = [f"from: {self.sender}", f"to: {self.to}"]
        if self.title:
            head.append(f"title: {self.title}")
        if self.reply_to:
            head.append(f"reply_to: {self.reply_to}")
        if self.status:
            head.append(f"status: {self.status}")
        if self.revises:
            head.append(f"revises: {self.revises}")
        if self.supersedes:
            head.append(f"supersedes: {self.supersedes}")
        if self.service:
            versions = [f"{k} v{v}" for k, v in (("contract", self.contract), ("playbook", self.playbook)) if v is not None]
            head.append(f"service: {self.service}" + (f" ({', '.join(versions)})" if versions else ""))
        if self.feedback:
            head.append(f"feedback: {self.feedback}")
        if self.source:
            head.append(f"source: {self.source}")
        if self.criterion:
            head.append(f"criterion: {self.criterion}")
        if self.acknowledges:
            head.append(f"acknowledges: {self.acknowledges}")
        if self.budget and self.type == "result":
            head.append(f"returns {self.budget} run(s)")
        elif self.budget:
            head.append(f"budget: {self.budget} runs")
        body = self.cut_body(limit)
        return f"### {self.type} {self.id}\n" + " | ".join(head) + f"\n\n{body}\n"


def verdict_tier(note: Message) -> str:
    """The weight class of a client's verdict or link note: "agent" when an agent sent it (its client is an LLM), else its
    ``source``; a root note without one (written before sources existed) is "human", an unknown value "relayed".
    Only "human" weighs anything in a gate."""
    if note.sender != ROOT:
        return "agent"
    if note.source is None:
        return "human"
    return note.source if note.source in SOURCES else "relayed"


def link_ids(note: Message) -> tuple[str, ...]:
    """The ids in a note's ``criterion`` field, in order, without blanks ("C6, R2" -> ("C6", "R2"))."""
    return tuple(part for part in (p.strip() for p in (note.criterion or "").split(",")) if part)


RUN_CREDIT_TITLE = "run credit"  # the title of the note with which the runtime returns a run it does not charge: "run credit <addr>@<run-log stem>"


def run_credit_title(addr: str, stem: str) -> str:
    """The title of the credit for ``addr``'s run whose log is ``<stem>.log``."""
    return f"{RUN_CREDIT_TITLE} {addr}@{stem}"


def _credited_stem(note: Message) -> str:
    """The run-log stem a run credit returns, else ``""``: a note of the runtime that carries runs and whose title names its own recipient."""
    prefix = f"{RUN_CREDIT_TITLE} {note.to}@"
    credited = note.sender == RUNTIME and note.type == "note" and note.budget > 0 and note.title.startswith(prefix)
    return note.title[len(prefix):] if credited else ""


def is_run_credit(note: Message) -> bool:
    """The note is a run credit: it returns one run to the agent it was sent to (budget is derived, so the note is the credit)."""
    return bool(_credited_stem(note))


def credited_stems(received: Iterable[Message]) -> set[str]:
    """The stems of the run logs that a received box credits: those runs are not charged."""
    return {stem for stem in map(_credited_stem, received) if stem}


def latest_results(results: Iterable[Message]) -> dict[str, Message]:
    """The latest result per task id (``reply_to``): the task's current outcome.

    Ids start with a microsecond timestamp, so the highest id is the latest. A ``blocked`` result can be superseded by
    a later one; ``done`` and ``failed`` are final, so anything derived from "the status of a task" uses this.
    """
    out: dict[str, Message] = {}
    for m in results:
        if m.type == "result" and m.reply_to and (m.reply_to not in out or m.id > out[m.reply_to].id):
            out[m.reply_to] = m
    return out
