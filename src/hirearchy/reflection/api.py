"""The public surface of ``reflection``: what the history of the requests for a service shows, derived from the message files.

A *case* is one request for a service plus its rework chain (a rework is a request sent back with ``revises``); the client's *verdicts* are the
quiet ``feedback`` notes on it. Everything here is DERIVED: nothing is stored, the cases are read again from the mailboxes and the run logs each
time, so they can never disagree with the files. They feed three readers:

* the owner of the service, whose run prompt carries its playbook and, before a new request or after a rejection, a digest of the cases with
  new evidence to reflect on (``ReflectionDigest``, ``ServicePromptSections``);
* the client, who sees the record of each service (``ServiceReports.services_text``) and the totals of a case (``case_total``);
* ``progress`` and the dashboard, which show a case and its statistics (``CaseHistory``, ``summarize``, ``stats_by_version``).

The contracts and playbooks are ``services``' (``ServiceCatalog``); this package only reads them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from ..kernel import Message, client_questions, msg_time
from ..services import Criterion

__all__ = [
    "Assertion",
    "Case",
    "CaseHistory",
    "ReflectionDigest",
    "ServicePromptSections",
    "ServiceReports",
    "ServiceSteps",
    "Stats",
    "StatsReport",
    "Verdict",
    "case_spend",
    "confirmed_criteria",
    "delivered_unrated",
    "lessons_of",
    "questions_open",
    "rated",
    "regressions",
    "stats_by_version",
    "summarize",
    "version_at",
]


@dataclass
class Verdict:
    """One client verdict on a case: ``step`` is 0 for the first delivery, n for the n-th rework."""

    verdict: str
    note: str  # the client's own words ("" for a bare accept)
    created: datetime | None
    task_id: str  # the task of the chain the feedback was given on
    step: int
    message: Message
    tier: str = "human"  # its weight class: ``kernel.verdict_tier`` of the note (human | relayed | agent)
    links: tuple[str, ...] = ()  # what the client said it was about: the effective link (C<k>, R<k> or none), () when there is none
    links_tier: str = ""  # the tier of the note that carries the effective link ("" = no link)
    confirmed: tuple[str, ...] = ()  # the C<k> ids named by every human-tier link note of this verdict (never by its own criterion), in note order
    link_notes: tuple[Message, ...] = ()  # the link notes that reply to this verdict, of every tier, in id order (a cited note id is evidence, 4.3)


@dataclass
class Case:
    """One request of a service plus its rework chain (derived from the message files)."""

    id: str  # id of the first request
    service: str
    owner: str
    tasks: list[Message]  # the request and its reworks, oldest first
    result: Message | None  # latest result of the latest task
    state: str  # open | done | failed | blocked
    playbook: int  # version of the playbook when the first request was sent
    used: int  # version in force when the case was first answered (now, if still unanswered): what the stats group by
    reworks: int
    budget: int  # sum of the budgets of the tasks
    runs: int  # runs of the owner's subtree from the first request to the final result (or now)
    lessons: list[str]  # from the `## Lessons` sections of the results, oldest first
    verdicts: list[Verdict]  # every client verdict on the case, oldest first (the latest is the final one)
    started: datetime | None
    finished: datetime | None  # when it ended done/failed
    lesson_ids: list[str] = field(default_factory=list)  # id of the result each lesson came from (parallel to lessons)
    lesson_sources: list[str] = field(default_factory=list)  # the ``source`` of the task each lesson's result answers: relayed | human | "" (parallel)
    client_kind: str = "human"  # "human" when the owner's parent is root, else "agent"
    relayed_reworks: int = 0  # the tasks of the chain after the first that root stamped ``source: relayed``
    returned: int = 0  # the runs the results of the chain carried back: each result counts at most its own task's budget

    @property
    def title(self) -> str:
        return self.tasks[0].title

    @property
    def feedback(self) -> Message | None:
        """The latest feedback note (the final verdict), None when the client has not rated the case."""
        return self.verdicts[-1].message if self.verdicts else None

    @property
    def verdict(self) -> str | None:
        """The final verdict: that of the latest feedback."""
        return self.verdicts[-1].verdict if self.verdicts else None

    @property
    def rejected(self) -> bool:
        """Was the case rejected at least once, whatever came after?"""
        return any(v.verdict == "reject" for v in self.verdicts)

    @property
    def accepted_after_reject(self) -> bool:
        return self.verdict == "accept" and self.rejected

    @property
    def evidence_at(self) -> datetime | None:
        """The latest moment this case produced evidence: its final result or its latest feedback."""
        times = [t for t in (self.finished, msg_time(self.feedback) if self.feedback else None) if t]
        return max(times) if times else None


@dataclass(frozen=True)
class Assertion:
    """One regression assertion: a rejection by the human client, numbered ``R<k>`` in the order of the notes (derived by :func:`regressions`)."""

    id: str  # "R<k>"
    case: str  # the id of the case the rejection belongs to
    verdict: Verdict
    about: tuple[str, ...]  # the criteria (C<k>) the client confirmed it is about, "the same as R<j>" resolved; an R<j> that is about nothing stays
    link: str  # "confirmed" (a human link naming ids) | "none" (a human link "none": no lasting rule) | "unconfirmed" (only a relayed link) | ""


def case_spend(case: Case) -> int:
    """The runs a case costs against its contract's per-request budget (pure): the runs its team used, plus, while it is not finished (open or
    blocked), the runs handed down for it that were neither used nor returned (the team may still spend them). ``case_total`` warns on it;
    Phase 0b's cost alarm reads the same number."""
    still_out = 0 if case.state in ("done", "failed") else max(0, case.budget - case.runs - case.returned)
    return case.runs + still_out


def confirmed_criteria(cases: Sequence[Case], criteria: Sequence[Criterion]) -> frozenset[str]:
    """The C<k> ids the human client confirmed: the ids in ``v.confirmed`` (named by a human-tier link note), over every verdict of ``cases``
    (pure). A criterion on the rejection itself, a link "the same as R<j>" and "none" confirm no criterion.

    ``criteria`` (the service's, with their basis) decide which link counts for which criterion: one added by an answered amendment
    (``Criterion.answers``) is confirmed only by a human link on that rejection (the product's own link), one the user asked for on their own
    (``Criterion.user``) never; any other (v1, an agent's version, a version written before 0a.2) as in 0a.1, by any human link."""
    basis = {c.id: c for c in criteria}

    def counts(v: Verdict, x: str) -> bool:
        c = basis.get(x)
        return c is None or not (c.user or (c.answers and c.answers != v.message.id))

    return frozenset(x for c in cases for v in c.verdicts for x in v.confirmed if counts(v, x))


def rated(case: Case | None, task: Message) -> bool:
    """Has the client given a verdict (any tier) on this delivery or on a later rework of it? An earlier verdict does not count (pure)."""
    if case is None:
        return False
    step = next((i for i, t in enumerate(case.tasks) if t.id == task.id), 0)
    return any(v.step >= step for v in case.verdicts)


def questions_open(task: Message, result: Message, case: Case | None, root_sent: Sequence[Message]) -> int:
    """The client questions (``kernel.client_questions``) of a ``done`` or ``blocked`` result that nothing has settled (pure): 0 when there are none,
    when ``task`` is a service request and ``rated(case, task)``, or when ``root_sent`` holds a task with ``revises == task.id`` and ``source ==
    "human"``; else their number. The user's own rework of the task or the client's verdict on the delivery settles them; the assistant's own
    (relayed) rework does not (0a.1 DR-17). ``progress`` withholds the artifact path while this is above 0 and the deliverable checks do the same."""
    if result.status not in ("done", "blocked"):
        return 0
    asked = len(client_questions(result.body))
    if asked == 0 or (task.service and rated(case, task)):
        return 0
    reworked = any(t.type == "task" and t.revises == task.id and t.source == "human" for t in root_sent)
    return 0 if reworked else asked


def delivered_unrated(cases: Sequence[Case]) -> tuple[str, ...]:
    """The latest task id of every case that is delivered (``state == "done"``) and whose latest task has no verdict (pure). A case that is blocked,
    failed or still open has no delivery to rate."""
    return tuple(c.tasks[-1].id for c in cases if c.state == "done" and not rated(c, c.tasks[-1]))


def regressions(cases: Sequence[Case]) -> list[Assertion]:
    """The human-tier rejections of ``cases``, ordered by their note ids: ``R<k>`` is the k-th (pure).

    Relayed and agent rejections are never assertions; a case rejected and then accepted keeps its assertions. What an assertion is about comes
    only from human-tier links ("the same as R<j>" is resolved through the links of R<j>, a cycle ends where it started)."""
    found = sorted(((v, c.id) for c in cases for v in c.verdicts if v.verdict == "reject" and v.tier == "human"), key=lambda item: item[0].message.id)
    ids = [f"R{k}" for k in range(1, len(found) + 1)]

    def human(v: Verdict) -> tuple[str, ...]:
        return v.links if v.links_tier == "human" else ()

    def about(k: int, seen: frozenset[str]) -> tuple[str, ...]:
        out: list[str] = []
        for x in human(found[k][0]):
            if x == "none":
                continue
            if x.startswith("C"):
                out.append(x)
            elif x[1:].isdigit() and 1 <= int(x[1:]) <= len(found) and x != ids[k] and x not in seen:
                inner = about(int(x[1:]) - 1, seen | {ids[k]})
                out.extend(inner or (x,))
        return tuple(dict.fromkeys(out))

    def link(v: Verdict) -> str:
        if human(v) == ("none",):
            return "none"
        return "confirmed" if human(v) else "unconfirmed" if v.links else ""

    return [Assertion(ids[k], case, v, about(k, frozenset()), link(v)) for k, (v, case) in enumerate(found)]


@runtime_checkable
class StatsReport(Protocol):
    """What the counts of a set of cases can say of themselves: how many ended, how many runs they took on average, and the one-line record."""

    @property
    def finished(self) -> int:
        """Cases that ended: done plus failed."""
        ...

    @property
    def avg_runs(self) -> float | None:
        """Runs per finished case (one decimal); None when none finished."""
        ...

    def line(self) -> str:
        """``3 request(s): 2 done, 0 failed, 1 open; 1 reworked; avg 4 runs; feedback 1 accept (1 after a reject), 1 reject``."""
        ...


@dataclass
class Stats(StatsReport):
    requests: int = 0
    done: int = 0
    failed: int = 0
    open: int = 0
    reworked: int = 0
    accept: int = 0  # final verdict accept (including the ones that came after a reject)
    reject: int = 0  # final verdict reject
    accept_after_reject: int = 0  # of the accepts: cases the client had rejected at least once before
    finished_runs: int = 0

    @property
    def finished(self) -> int:
        return self.done + self.failed

    @property
    def avg_runs(self) -> float | None:
        return round(self.finished_runs / self.finished, 1) if self.finished else None

    def line(self) -> str:
        text = f"{self.requests} request(s): {self.done} done, {self.failed} failed, {self.open} open; {self.reworked} reworked"
        if self.avg_runs is not None:
            text += f"; avg {self.avg_runs:g} runs"
        if self.accept or self.reject:
            after = f" ({self.accept_after_reject} after a reject)" if self.accept_after_reject else ""
            text += f"; feedback {self.accept} accept{after}, {self.reject} reject"
        else:
            text += "; no feedback"
        return text


def summarize(items: Sequence[Case]) -> Stats:
    """Counts over cases: requests, done, failed, open (incl. blocked), reworked, average runs of finished, verdicts."""
    s = Stats(requests=len(items))
    for c in items:
        s.done += c.state == "done"
        s.failed += c.state == "failed"
        s.open += c.state in ("open", "blocked")
        s.reworked += c.reworks > 0
        s.accept += c.verdict == "accept"
        s.reject += c.verdict == "reject"
        s.accept_after_reject += c.accepted_after_reject
        s.finished_runs += c.runs if c.state in ("done", "failed") else 0
    return s


def stats_by_version(items: Sequence[Case]) -> dict[int, Stats]:
    """:func:`summarize` per playbook version, grouped by the version in force when each case was first answered.

    (Not the version current when the request was sent: the owner typically revises the playbook right after the
    request arrives, and that request is then delivered under the new version.)
    """
    return {v: summarize([c for c in items if c.used == v]) for v in sorted({c.used for c in items})}


def version_at(timeline: Sequence[tuple[int, datetime]], when: datetime | None) -> int:
    """The playbook version in force at ``when`` (None = now): the latest written at or before it; 0 if none yet."""
    return max((v for v, t in timeline if when is None or t <= when), default=0)


def lessons_of(result: Message) -> str:
    """The text of the ``## Lessons`` section of a result body ("" if there is none)."""
    out, inside = [], False
    for line in result.body.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower() == "lessons"
        elif inside:
            out.append(line)
    return "\n".join(out).strip()


@runtime_checkable
class CaseHistory(Protocol):
    def cases(self, owner: str, service: str) -> list[Case]:
        """Every case of ``owner``'s service, oldest first: requests plus their rework chains, with results and feedback.

        Runs: all run logs of the owner's subtree from the first request to the final result (or now), ending early where the client's next task
        to the same owner begins - the same window rule as ``progress`` - so overlapping cases do not count a run twice. Requests from before
        the service was (last) created from scratch are not part of it. ``[]`` when there is no such service."""
        ...

    def case_of(self, task: Message) -> Case | None:
        """The case a service task belongs to (None for a task that is not a service request, or an unknown one)."""
        ...

    def playbook_timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        """(version, when it was written) of every playbook version the service has had, oldest first."""
        ...


@runtime_checkable
class ReflectionDigest(Protocol):
    def reflection_digest(self, owner: str, service: str) -> str | None:
        """Evidence since the current playbook was revised, as a compact markdown block; None when there is none.

        New evidence = a case that finished, or feedback that was given, after the playbook's ``revised`` time (without a playbook: any finished
        case or feedback). The block lists the most recent cases with new evidence (at most 6: state, runs used of the budget given, reworks, the
        client's verdict and note, lessons - each clipped), then one line of statistics per playbook version. About 3000 characters at most."""
        ...


@runtime_checkable
class ServiceReports(Protocol):
    def services_text(self, actor: str) -> str:
        """The `services` tool/CLI output: what ``actor`` can request from its direct reports, and what it offers."""
        ...

    def case_total(self, task: Message) -> str:
        """The whole case in one sentence: runs used by the chain against the runs handed down, and the contract's budget.

        ``case total: 19 runs used of 27 handed down (contract: 15 per request)``; when the runs used, plus the runs still out on an open case
        (``case_spend``), exceed the contract's budget, it adds that the case exceeds the budget and that the user must be told. Empty for a task that is not a service request."""
        ...


@runtime_checkable
class ServiceSteps(Protocol):
    """What root is told to do next after it records a rejection or sends a rework: advice that names the one question to ask the user and the
    calls that record their answer, or the questions the client was already asked. No step follows an amendment: the gate refuses one that does
    not carry the user's words. Read-only: it never writes, and root is the only one who reads it (an agent never sees a step)."""

    def feedback_step(self, note: Message) -> str:
        """What root does next after recording ``note``, a verdict note: for a human-tier rejection of a service request, the one question naming
        an id and the confirmation call; "" for an accept, a relayed or agent rejection, a link note or a note it cannot place."""
        ...

    def rework_step(self, task: Message) -> str:
        """For a rework root just sent with ``source: relayed`` (``task``, a request that ``revises`` another), the client questions of the latest
        result of the request it revises, in one sentence that tells root to ask the user (a rework does not answer them); "" for a rework the
        user asked for, a result without a ``Questions for the client:`` block, or a request it cannot place. A nudge: nothing is refused."""
        ...


@runtime_checkable
class ServicePromptSections(Protocol):
    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        """The sections of an owner's run prompt: its services, the playbook of each service it has an open request for, and (when the batch
        holds a new request, or the client's rejection of a delivery) what to reflect on first. Empty for an agent that owns no service.

        Each section starts and ends with a newline, to be appended after the notice and before "# New messages"."""
        ...
