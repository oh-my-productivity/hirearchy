"""A world of mail for the tests of the watch (no test lives here): the client's requests and verdicts, the owner's results, contract versions and
playbook versions, each at a tick the test chooses. The cases are the real ``DerivedCaseHistory``'s, built from the mail alone.

A tick is a second after ``BASE``; ``us`` adds microseconds, for the rows that need two records at one instant. Every id is ``<stamp>-<name>``."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from hirearchy.kernel import ROOT, STAMP_FORMAT, Message
from hirearchy.mail import MailboxReader
from hirearchy.reflection import Case
from hirearchy.reflection._cases import DerivedCaseHistory
from hirearchy.reflection._watch import Records, records_of
from hirearchy.services import Contract

OWNER = "ceo"
SERVICE = "weekly-brief"
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def stamp(tick: int, us: int = 0) -> datetime:
    return BASE + timedelta(seconds=tick, microseconds=us)


def mid(tick: int, name: str, us: int = 0) -> str:
    return f"{stamp(tick, us):{STAMP_FORMAT}}-{name}"


class _Mail(MailboxReader):
    """The two boxes ``DerivedCaseHistory`` reads: what root sent and what root received."""

    def __init__(self, sent: Sequence[Message], received: Sequence[Message]) -> None:
        self._sent = sorted(sent, key=lambda m: m.id)
        self._received = sorted(received, key=lambda m: m.id)

    def sent(self, addr: str) -> list[Message]:
        return list(self._sent)

    def received(self, addr: str) -> list[Message]:
        return list(self._received)

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        return []

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        return None

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        return None

    def unread(self, addr: str) -> int:
        return 0

    def has_inflight(self, addr: str) -> bool:
        return False


class _Agents:
    def subtree(self, addr: str) -> list[str]:
        return [addr]

    def exists(self, addr: str) -> bool:
        return True


class _Words:
    def feedback_text(self, msg: Message) -> str:
        return msg.body


@dataclass
class Mailbag:
    """What the client sent and received, filled in by the test."""

    sent: list[Message] = field(default_factory=list)
    received: list[Message] = field(default_factory=list)

    def ask(self, name: str, tick: int, *, revises: str | None = None, source: str | None = None, us: int = 0) -> Message:
        """A request (or, with ``revises``, a rework) of the service; its id is the task id the other calls take."""
        task = Message(
            sender=ROOT, to=OWNER, type="task", body="Do it.", title=name, service=SERVICE, revises=revises, source=source, budget=3,
            id=mid(tick, name, us),
        )
        self.sent.append(task)
        return task

    def answer(self, task: Message, tick: int, status: str = "done", *, name: str | None = None, us: int = 0) -> Message:
        """The owner's result on ``task``: ``done``, or ``blocked`` (a blocked result is no delivery)."""
        result = Message(
            sender=OWNER, to=ROOT, type="result", status=status, reply_to=task.id, body="Delivered.", title="Result",
            id=mid(tick, name or f"{task.title}.{status}", us),
        )
        self.received.append(result)
        return result

    def verdict(
        self, task: Message, tick: int, kind: str, *, source: str = "human", words: str = "No.", name: str | None = None, us: int = 0,
    ) -> Message:
        """The client's verdict note on ``task``: ``accept`` or ``reject`` (``source`` is its tier: ``human`` or ``relayed``)."""
        note = Message(
            sender=ROOT, to=OWNER, type="note", body=words, title="feedback", feedback=kind, reply_to=task.id, source=source,
            id=mid(tick, name or f"{task.title}.{kind}", us),
        )
        self.sent.append(note)
        return note

    def link(self, verdict: Message, tick: int, *ids: str, source: str = "human", name: str | None = None, us: int = 0) -> Message:
        """What the client says ``verdict`` is about: a link note (``C6``, ``R2``, ``none``), human tier unless ``source`` says otherwise."""
        note = Message(
            sender=ROOT, to=OWNER, type="note", body="About.", title="link", reply_to=verdict.id, source=source, criterion=", ".join(ids),
            id=mid(tick, name or f"{verdict.title}.link{tick}", us),
        )
        self.sent.append(note)
        return note

    def cases(self) -> list[Case]:
        nothing: Any = None  # the ports a case read from the mail alone never touches (no contract, no run log, no charter)
        history = DerivedCaseHistory(nothing, cast(Any, _Agents()), _Mail(self.sent, self.received), cast(Any, _Words()), nothing, nothing, nothing)
        return history.chains(OWNER, SERVICE, since=None, runs=False)

    def results(self) -> dict[str, tuple[Message, ...]]:
        """Every result of every task, oldest first (the watch's ``results``)."""
        out: dict[str, list[Message]] = {}
        for m in sorted(self.received, key=lambda m: m.id):
            if m.type == "result" and m.reply_to:
                out.setdefault(m.reply_to, []).append(m)
        return {task: tuple(found) for task, found in out.items()}


def contract(
    version: int, acceptance: Sequence[str], tick: int, *, answers: str = "", about: str = "", by: str = ROOT, initiated: str = "",
    created: datetime | None = None, us: int = 0,
) -> Contract:
    """A stored version of the service's contract, defined at ``tick`` (its ``created`` is v1's, as every version carries it)."""
    return Contract(
        name=SERVICE, owner=OWNER, acceptance=list(acceptance), version=version, defined_by=by, defined=stamp(tick, us),
        created=created or stamp(0), answers=answers, about=about, initiated=initiated,
    )


def records(bag: Mailbag, *contracts: Contract) -> Records:
    return records_of(bag.cases(), bag.results(), list(contracts))
