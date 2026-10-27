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
from hirearchy.reflection._watch import Records, records_of, watch_states
from hirearchy.services import Contract, ItemWatch, Playbook, PlaybookItem, number_criteria

OWNER = "ceo"
SERVICE = "weekly-brief"
AGENT = "boss"  # an agent client: its verdicts are hypotheses (tier agent)
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
        """The client's verdict note on ``task``: ``accept`` or ``reject`` (``source`` is its tier: ``human``, ``relayed`` or ``agent``)."""
        note = Message(
            sender=AGENT if source == "agent" else ROOT, to=OWNER, type="note", body=words, title="feedback", feedback=kind, reply_to=task.id,
            source=None if source == "agent" else source, id=mid(tick, name or f"{task.title}.{kind}", us),
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


def step(item_id: str, text: str, why: Sequence[str] = ()) -> PlaybookItem:
    return PlaybookItem(item_id, "step", "## Steps", text, "", tuple(why))


def rule(item_id: str, when: str, then: str, why: Sequence[str] = ()) -> PlaybookItem:
    return PlaybookItem(item_id, "rule", "## Rules", then, when, tuple(why))


def playbook(
    version: int, tick: int, items: Sequence[PlaybookItem], *, op: str, item: str = "", admitted: str = "", us: int = 0, restores: int = 0,
    related: Sequence[str] = (), parse_error: str = "",
) -> Playbook:
    """A stored version of the playbook in item form (``parse_error`` set: a hand-broken file that does not parse, with no items)."""
    return Playbook(
        version=version, revised=stamp(tick, us), by="runtime (watch)" if op == "watch" else OWNER, items=None if parse_error else tuple(items),
        items_max=max([int(i.id[1:]) for i in items], default=0), op=op, item=item, admitted=admitted,
        why={i.id: i.why for i in items if i.why}, related=tuple(related), restores=restores, parse_error=parse_error,
    )


@dataclass
class Watching:
    """One service under the watch: its contract versions, playbook versions and mail, and the states they derive."""

    bag: Mailbag = field(default_factory=Mailbag)
    contracts: list[Contract] = field(default_factory=list)
    versions: list[Playbook] = field(default_factory=list)
    notes: dict[str, Message] = field(default_factory=dict)  # the verdict note of each case ``case`` made, by the case's name
    tasks: dict[str, Message] = field(default_factory=dict)  # the request of each, by name

    def items(self, index: int) -> tuple[PlaybookItem, ...]:
        """The items of the ``index``-th playbook version."""
        return self.versions[index].items or ()

    def states(self) -> dict[str, ItemWatch]:
        stored = [(c.version, c.defined_by or "", c.acceptance) for c in self.contracts]
        criteria = number_criteria(stored, {c.version: (c.answers, c.initiated == "user") for c in self.contracts})
        found = watch_states(self.versions, self.bag.cases(), self.bag.results(), criteria, self.contracts)
        return {w.id: w for w in found}

    def case(
        self, name: str, ask: int, done: int | None = None, *, verdict: tuple[int, str] | None = None, link: tuple[int, Sequence[str]] | None = None,
        source: str = "human", status: str = "done", revises: Message | None = None, asked_by: str | None = None,
    ) -> Message:
        """A request at ``ask`` (a result ``status`` at ``done``), the client's verdict ``(tick, "accept" | "reject")`` on it and a human link to
        it ``(tick, [ids])``; returns the request. ``revises``: the request it sends back (a rework; ``asked_by`` is its ``source``)."""
        task = self.bag.ask(name, ask, revises=revises.id if revises is not None else None, source=asked_by)
        self.tasks[name] = task
        if done is not None:
            self.bag.answer(task, done, status)
        if verdict is not None:
            note = self.bag.verdict(task, verdict[0], verdict[1], source=source)
            self.notes[name] = note
            if link is not None:
                self.bag.link(note, link[0], *link[1])
        return task


def world(p1: str = "Read the request.") -> Watching:
    """The standard world of the watch's tests: contract v1 with C1-C6 (C5 is "e"); playbook v1 (a step, never watched); R1, the rejection of case c0
    answered about C5; and P2, a rule admitted at tick 10 on R1 and C5 (rule (c)), whose watch these tests read with k = 3."""
    w = Watching()
    w.contracts.append(contract(1, ["a", "b", "c", "d", "e", "f"], 0))
    first = [step("P1", p1)]
    w.versions.append(playbook(1, 0, first, op="first", admitted="first"))
    w.case("c0", 1, 2, verdict=(3, "reject"), link=(4, ["C5"]))
    rule2 = rule("P2", "a date is relative", "convert it from the date of the request", why=("R1", "C5"))
    w.versions.append(playbook(2, 10, [*first, rule2], op="add", item="P2", admitted="c"))
    return w
