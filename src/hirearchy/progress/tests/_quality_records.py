"""Builders of the records the quality renderer is tested with: tasks, results, verdicts, deliveries, cases and ``ServiceRecord``s (values, no files)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from hirearchy.kernel import ROOT, Message, msg_time
from hirearchy.reflection import (
    Assertion, Case, Cause, ContractMark, Delivery, ServiceRecord, TopUp, TopUps, Verdict,
)

SERVICE = "weekly-memo"
OWNER = "lead"


def mid(n: int, who: str = ROOT) -> str:
    """A message id: minute ``n`` (0-59) of 2026-10-21 15:00, in the order of ``n``."""
    return f"20261021T15{n:02d}00000000-{who}-{n:04d}"


def request(
    n: int, *, title: str = "Memo for the meeting", source: str | None = None, revises: str | None = None, budget: int = 5, to: str = OWNER,
    service: str | None = SERVICE,
) -> Message:
    return Message(
        id=mid(n), sender=ROOT, to=to, type="task", title=title, body="goal", budget=budget, service=service if to == OWNER else None, source=source,
        revises=revises, contract=1 if service else None,
    )


def done(of: Message, n: int, status: str = "done") -> Message:
    return Message(id=mid(n, of.to), sender=of.to, to=ROOT, type="result", title="re", body="Delivered.", reply_to=of.id, status=status)


def note(n: int, on: Message, verdict: str, words: str = "", source: str | None = None) -> Message:
    return Message(id=mid(n), sender=ROOT, to=on.to, type="note", title="feedback", body=words, feedback=verdict, reply_to=on.id, source=source)


def verdict(
    task: Message, n: int, kind: str = "reject", words: str = "words", *, step: int = 0, source: str | None = None, tier: str | None = None,
    confirmed: tuple[str, ...] = (), links: tuple[str, ...] = (), links_tier: str = "",
) -> Verdict:
    m = note(n, task, kind, words, source)
    return Verdict(
        kind, words, msg_time(m), task.id, step, m, tier=tier or ("relayed" if source == "relayed" else "human"), links=links, links_tier=links_tier,
        confirmed=confirmed,
    )


def case(
    tasks: list[Message], *, state: str = "done", verdicts: list[Verdict] | None = None, runs: int = 0, relayed_runs: int = 0, owner: str = OWNER,
    service: str = SERVICE, budget: int = 0, ceiling: int = 0, **more: Any,
) -> Case:
    made = Case(
        id=tasks[0].id, service=service, owner=owner, tasks=tasks, result=None, state=state, playbook=1, used=1, reworks=len(tasks) - 1, budget=budget,
        runs=runs, lessons=[], verdicts=verdicts or [], started=msg_time(tasks[0]), finished=None, relayed_runs=relayed_runs, user_ceiling=ceiling,
        client_kind="human" if tasks[0].sender == ROOT else "agent",
    )
    for key, value in more.items():
        setattr(made, key, value)
    return made


def delivery(
    c: Case, step: int = 0, *, result_n: int, signer: str = OWNER, verdicts: tuple[Verdict, ...] = (), superseded: str = "", edited_at: int = 0,
    edited: bool = False, given: bool = False,
) -> Delivery:
    task = c.tasks[step]
    return Delivery(c.id, task, done(task, result_n), step, signer, verdicts, superseded, edited_at, edited, given)


def contract_mark(version: int = 1, *, ids: tuple[str, ...] = ("C1", "C2")) -> ContractMark:
    return ContractMark(version, datetime(2026, 10, 21, 15, 23, tzinfo=timezone.utc), ROOT, ids, (), "first")


def record(
    *, cases: list[Case] | None = None, deliveries: tuple[Delivery, ...] = (), escapes: tuple[tuple[Delivery, Cause], ...] = (), budget: int = 15,
    assertions: tuple[Assertion, ...] = (), owner: str = OWNER, service: str = SERVICE, timeline: tuple[Any, ...] = (), **more: Any,
) -> ServiceRecord:
    fields: dict[str, Any] = dict(
        owner=owner, service=service, client=ROOT, client_kind="human", contract=3, playbook=1, budget=budget, cases=tuple(cases or ()),
        deliveries=deliveries, escapes=escapes, assertions=assertions, timeline=timeline,
    )
    fields.update(more)
    return ServiceRecord(**fields)


def top_ups(*items: tuple[str, str, int]) -> TopUps:
    return TopUps(tuple(TopUp(i, kind, amount) for i, kind, amount in items))


@dataclass(frozen=True)
class StoredVersion:
    """The fields of a stored contract version that the lineage of a criterion reads (``progress`` may not import ``services``, where ``Contract`` is)."""

    version: int
    acceptance: list[str]
    defined: datetime
    answers: str = ""
    defined_by: str = ROOT
    initiated: str = ""


def lineage_record() -> ServiceRecord:
    """R1 is about C6, which contract v2 replaced with C10; R2, later, is about C10: the repeat alarm reads them as one criterion (design 10.5)."""
    t1, t2 = request(3), request(9)
    v1_, v2_ = verdict(t1, 5, "reject", "No.", confirmed=("C6",)), verdict(t2, 11, "reject", "No again.", confirmed=("C10",))
    link = Message(id=mid(12), sender=ROOT, to=OWNER, type="note", title="link", body="About.", reply_to=v2_.message.id, criterion="C10", source="human")
    v2_.link_notes = (link,)
    one, two = case([t1], verdicts=[v1_]), case([t2], verdicts=[v2_])
    d1, d2 = delivery(one, 0, result_n=4, verdicts=(v1_,)), delivery(two, 0, result_n=10, verdicts=(v2_,))
    nine = ["w", "x", "y", "z", "u", "v", "q", "r", "s"]  # C1-C9: "v" is C6
    first = StoredVersion(1, nine, datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc))
    second = StoredVersion(2, [*nine[:5], "ten", *nine[6:]], datetime(2026, 10, 21, 15, 7, tzinfo=timezone.utc), answers=v1_.message.id)
    a1, a2 = Assertion("R1", one.id, v1_, ("C6",), "confirmed"), Assertion("R2", two.id, v2_, ("C10",), "confirmed")
    return record(cases=[one, two], deliveries=(d1, d2), assertions=(a1, a2), contracts=(first, second))
