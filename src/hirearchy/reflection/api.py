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

from ..kernel import ClientItems, Message, client_items, clip_line, msg_time
from ..services import Criterion
from ._deliverables import FOLDER_SHOWN, NAME_SHOWN, shown_name

__all__ = [
    "Assertion",
    "Case",
    "CaseHistory",
    "DeliverableChecks",
    "DeliverableFinding",
    "ITEMS_SHOWN",
    "ITEM_CHARS",
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
    "deliverables_note",
    "items_listing",
    "lessons_of",
    "open_client_items",
    "questions_open",
    "rated",
    "regressions",
    "stats_by_version",
    "summarize",
    "user_approved",
    "user_committed",
    "user_cost",
    "user_held",
    "user_spend",
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
    relayed_runs: int = 0  # 0b 4.2: the charged runs whose stamp lies in the interval of a relayed task, from its send to its successor's (the window's end for the last task, inclusive)
    relayed_returned: int = 0  # the runs the results of the relayed tasks carried back: each counts at most its own task's budget
    relayed_to_user: int = 0  # the user's runs that results of relayed tasks carried back beyond what each relayed task still had (D-E6-2); 0 for an agent client and without a relayed task
    relayed_overlap: int = 0  # the most of an unanswered relayed task's runs that can lie in a later user interval (its split is by send time)
    unsplit_runs: int = 0  # the charged runs in the user intervals after the first overlapped relayed task: counted with the user's, 0 without overlap
    user_granted: int = 0  # the budgets of the user grants: notes of a human client (root) in a user interval; 0 for an agent client
    open_tasks: tuple[str, ...] = ()  # the chain's tasks whose latest result is missing or blocked, oldest first (D-E6-2)
    user_ceiling: int = 0  # the highest ceiling over the user's hand-downs (the most the user's requests could cost right after one), leaving out the default's 1-run hand-downs with nothing left (``unapproved_reworks``, D-E7-2 A2); 0 for an agent client
    unapproved_reworks: tuple[str, ...] = ()  # D-E7-2 A2: the human reworks handed the default's 1 run while nothing was left (or an explicit 1 then, which the files cannot tell apart), oldest first: no approval of the user's; () for an agent client

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
    blocked), the runs handed down for it that were neither used nor returned (the team may still spend them). It is the case's total, the
    user's requests and root's relayed reworks together: ``case_total`` warns on it for an agent client's case, and D-E5-6 has Phase 0b's cost
    alarm split it (``user_cost`` against ``user_approved``, the comparison ``case_total`` makes for a human client's case)."""
    still_out = 0 if case.state in ("done", "failed") else max(0, case.budget - case.runs - case.returned)
    return case.runs + still_out


def _user_back(case: Case) -> int:
    """What came back of the user's runs: their own results' returns (each at most its task's budget) and the user's runs that relayed results
    carried back (``relayed_to_user``). The one helper of ``user_spend`` and ``user_committed``."""
    return case.returned - case.relayed_returned + case.relayed_to_user


def user_spend(case: Case) -> int:
    """The runs a case costs the user (pure): ``case_spend`` restricted to the user's requests, the tasks of the chain that are not relayed
    reworks, less the user's runs that a relayed result carried back (``_user_back``). Equal to ``case_spend`` when the chain has no relayed
    rework."""
    runs = case.runs - case.relayed_runs
    if case.state in ("done", "failed"):
        return runs
    budget = sum(t.budget for t in case.tasks if t.source != "relayed")
    return runs + max(0, budget - runs - _user_back(case))


def user_cost(case: Case) -> int:
    """The runs the user's requests cost at least (pure): ``user_spend`` less the runs of relayed reworks that can lie in a user's interval
    (``case.relayed_overlap``). The warning of ``case_total``, and 0b's cost alarm, compare it with ``user_approved`` (D-E5-6)."""
    return max(0, user_spend(case) - case.relayed_overlap)


def user_committed(case: Case) -> int:
    """What the user's requests used or the team still holds for them, whatever the case's state (pure): what a new rework draws on. The user's
    runs that a relayed result carried back (``_user_back``) are no longer held."""
    runs = case.runs - case.relayed_runs
    budget = sum(t.budget for t in case.tasks if t.source != "relayed") + case.user_granted
    return runs + max(0, budget - runs - _user_back(case))


def user_held(case: Case, rework: Message) -> int:
    """The user's runs the team still holds for the case when ``rework`` (a task of the case root just sent) revises a task that is still open:
    what the user's requests and grants handed down, less the user's charged runs and what came back to the user, less the rework's own budget,
    at least 0 (pure). 0 when the revised task has a done or failed result, or is not a task of the case. Read when the rework is sent: its own
    runs are not counted then."""
    if not rework.revises or rework.revises not in case.open_tasks:
        return 0
    return max(0, user_committed(case) - (case.runs - case.relayed_runs) - rework.budget)


def user_approved(case: Case, budget: int) -> int:
    """The runs the user approved for a case (pure): the contract's per-request ``budget``, raised to the highest ceiling root set for the
    user's requests (``case.user_ceiling``; 0 for an agent client, whose case therefore reads the contract's budget). ``case.user_ceiling`` leaves out
    the default's 1-run hand-downs with nothing left (``case.unapproved_reworks``), so only root's own hand-downs raise it (D-E7-2 A2)."""
    return max(budget, case.user_ceiling)


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


def rated(case: Case | None, task: Message, *, human: bool = False) -> bool:
    """Has the client given a verdict on this delivery or on a later rework of it? Any tier; with ``human``, only the user's own (``tier ==
    "human"``, D-E7-2 C). An earlier verdict does not count (pure)."""
    if case is None:
        return False
    step = next((i for i, t in enumerate(case.tasks) if t.id == task.id), 0)
    return any(v.step >= step and (not human or v.tier == "human") for v in case.verdicts)


ITEM_CHARS = 160  # each listed client item is cut to this many characters
ITEMS_SHOWN = 5  # at most this many are listed; the rest are counted


def open_client_items(task: Message, result: Message, case: Case | None, root_sent: Sequence[Message]) -> ClientItems:
    """The client items (``kernel.client_items``: questions and notes) of a ``done`` or ``blocked`` result that nothing has settled (pure): none when
    there are none, when ``task`` is a service request and ``rated(case, task, human=True)``, or when ``root_sent`` holds a task with ``revises ==
    task.id`` and ``source == "human"``; else the split. The user's own rework of the task or the user's verdict (human tier) on the delivery or on a
    later rework of it settles questions and notes together; the assistant's own (relayed) rework or verdict settles neither (0a.1 DR-17; D-E7-2 C)."""
    if result.status not in ("done", "blocked"):
        return ClientItems()
    items = client_items(result.body)
    if not (items.questions or items.notes) or (task.service and rated(case, task, human=True)):
        return ClientItems()
    reworked = any(t.type == "task" and t.revises == task.id and t.source == "human" for t in root_sent)
    return ClientItems() if reworked else items


def questions_open(task: Message, result: Message, case: Case | None, root_sent: Sequence[Message]) -> int:
    """The questions for the client of a ``done`` or ``blocked`` result that nothing has settled (pure): the open client items that name a criterion
    id (``C<k>``; the others are notes, D-E6-1), counted as ``open_client_items`` settles them: only the user's own rework or human-tier verdict
    does (D-E7-2 C). ``progress`` withholds the artifact path while this is above 0 and the deliverable checks do the same."""
    return len(open_client_items(task, result, case, root_sent).questions)


def items_listing(items: Sequence[str]) -> str:
    """``items`` for a sentence (pure): each cut to ``ITEM_CHARS`` characters, at most ``ITEMS_SHOWN`` of them joined with ``; ``, then ``; and {k}
    more`` when more remain."""
    shown = [clip_line(i, ITEM_CHARS) for i in items[:ITEMS_SHOWN]]
    more = len(items) - len(shown)
    return "; ".join(shown) + (f"; and {more} more" if more > 0 else "")


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
        (``case_spend``), exceed the contract's budget, it adds that the case exceeds the budget and that the user must be told. For a human
        client, the runs of root's relayed reworks are named apart and called root's own spend; when the user's requests cost more than the user
        approved (``user_cost`` against ``user_approved``) it adds that the user must be told; the default's 1-run hand-down with nothing left is no approval
        of the user's (D-E7-2 A2). An agent client's case reads as before 0a.3.
        Empty for a task that is not a service request."""
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
        """For a rework root just sent (``task``, a request that ``revises`` another): with source "relayed", the client questions of the revised
        request's latest result; with source "human", the top-up to ask the user for when the rework has less than one client round of the owner's
        team (1, plus 2 per agent below the owner) and the runs the user approved but has not used do not cover it; "" otherwise, and always for an
        agent client's case. While the revised task is still open (no result, or a blocked one), the user's runs the team still holds for the case
        count toward the round; when they cover it, the step says so instead of asking. When the rework is the default's 1 run with nothing left
        (``Case.unapproved_reworks``), the top-up asks for that run too and its grant is what it asks; when the runs the team holds cover the round,
        the ``HELD`` sentence is followed by one that tells root to say that run is beyond the user's approval (D-E7-2 A1). A nudge: nothing is
        refused."""
        ...


@runtime_checkable
class ServicePromptSections(Protocol):
    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        """The sections of an owner's run prompt: its services, the playbook of each service it has an open request for, and (when the batch
        holds a new request, or the client's rejection of a delivery) what to reflect on first. Empty for an agent that owns no service.

        Each section starts and ends with a newline, to be appended after the notice and before "# New messages"."""
        ...


@dataclass(frozen=True)
class DeliverableFinding:
    """One thing the check found in a contract's deliverable folder (or at its file): a file the team did not deliver as checked, or a place it could
    not read."""

    folder: str  # the folder as resolved (for a contract that names a file: that file's folder)
    services: tuple[str, ...]  # every service whose contract names this folder (or this file), sorted
    name: str  # the file name inside it ("" for the folder itself)
    kind: str  # "differs" | "relayed" | "unknown" | "link" | "large" | "limit" | "unreadable"
    artifact: str = ""  # the team's artifact it was compared with ("" unless "differs")
    task: str = ""  # the task whose done result last listed that artifact ("" unless "differs"); for "relayed": the delivery the file equals
    withheld: bool = False  # that result still has open client questions (``questions_open`` > 0): its artifact path is not shown
    error: str = ""  # for "unreadable": the operating system's words for it
    file: bool = False  # the contract names this file itself, not a folder
    relayed: tuple[str, ...] = ()  # for "relayed": the ids of root's relayed reworks that changed the team's copy after that delivery, oldest first


@runtime_checkable
class DeliverableChecks(Protocol):
    def findings(self, actor: str, service: str | None = None) -> list[DeliverableFinding]:
        """The files in the deliverable folders (``deliverable.path`` of the contracts) of the services ``actor`` requests (or only the folder of
        ``service``) that differ from the team's last checked version, that the team never wrote, or that could not be read; the ones the user's own
        verdict settled are left out. Never reads outside a folder; never raises for an unreadable folder, file or history (a catalog or a mailbox
        that cannot be read does raise ``OrgError`` or ``OSError``)."""
        ...


_NOTE_HEAD = "Tell the user what changed and why; never patch a deliverable yourself (send it back with revises):"
_NOTE_LINES = 10  # file lines of one block that are shown; the rest is counted
_RELAYED_TAIL = "(your own reading, not the user's) changed the team's copy after that delivery, so the file is not a deviation."


def _what(f: DeliverableFinding) -> str:
    """What is wrong with the file, in words (the part of a line after the name)."""
    if f.kind == "differs":
        if f.withheld:
            return f"differs from the team's checked version (task {f.task}; path withheld: ask first)"
        return f"differs from {clip_line(f.artifact, FOLDER_SHOWN)} as the team checked it (task {f.task})"
    if f.kind == "unknown":
        return "never written by the team"
    if f.kind == "link":
        return "a link, not read (hirearchy reads only files inside the folder)"
    if f.kind == "large":
        return "not read (larger than 4 MiB)"
    if f.kind == "limit":
        return "not read (this check reads at most 32 MiB in all)"
    return f"cannot be read ({clip_line(f.error, NAME_SHOWN)})" if f.kind == "unreadable" else f.kind


def _services(f: DeliverableFinding) -> str:
    return ("service " if len(f.services) == 1 else "services ") + ", ".join(f"`{name}`" for name in f.services)


def _relayed_line(f: DeliverableFinding) -> str:
    """The one line of a ``relayed`` finding: the file is the delivery the team checked, and root's own rework changed the team's copy after it."""
    reworks = f"your relayed rework{'s' if len(f.relayed) > 1 else ''} {', '.join(f.relayed)} {_RELAYED_TAIL}"
    if f.file:
        return f"Deliverable file {shown_name(f'{f.folder}/{f.name}', FOLDER_SHOWN)} ({_services(f)}): it is the delivery of task {f.task} as the team checked it; {reworks}"
    return f"Deliverable folder {shown_name(f.folder, FOLDER_SHOWN)} ({_services(f)}): {shown_name(f.name, NAME_SHOWN)} is the delivery of task {f.task} as the team checked it; {reworks}"


def _block(key: tuple[str, tuple[str, ...]], found: Sequence[DeliverableFinding]) -> list[str]:
    """The block of a folder: its heading, at most 10 file lines, and the count of the rest."""
    folder, _ = key
    lines = [f"Deliverable folder {shown_name(folder, FOLDER_SHOWN)} ({_services(found[0])}): {len(found)} file(s) the team did not deliver as checked. {_NOTE_HEAD}"]
    lines += [f"- {shown_name(f.name, NAME_SHOWN)}: {_what(f)}" for f in found[:_NOTE_LINES]]
    if len(found) > _NOTE_LINES:
        lines.append(f"- and {len(found) - _NOTE_LINES} more")
    return lines


def deliverables_note(findings: Sequence[DeliverableFinding]) -> str:
    """The note root reads when files of a deliverable folder are not what the team delivered as checked (pure): one block per folder, at most 10 file
    lines each; a contract that names a file has a heading of its own, and a folder that cannot be read, or is a link, is one line; a ``relayed``
    finding is one line of its own, left out of the block's count. ``""`` for none.
    File names and folders are rendered by :func:`shown_name`: a name is a prompt-injection channel, so it is never shown raw."""
    entries: list[list[str] | tuple[str, tuple[str, ...]]] = []  # in the order of the findings: lines already made, or the key of a block
    blocks: dict[tuple[str, tuple[str, ...]], list[DeliverableFinding]] = {}
    for f in findings:
        place = shown_name(f.folder, FOLDER_SHOWN)
        if f.kind == "relayed":  # a line of its own, never counted in a block and never the reason for a heading
            entries.append([_relayed_line(f)])
        elif f.file:
            heading = f"Deliverable file {shown_name(f'{f.folder}/{f.name}', FOLDER_SHOWN)} ({_services(f)}): it is not what the team delivered as checked. {_NOTE_HEAD}"
            entries.append([heading, f"- {_what(f)}"])
        elif not f.name and f.kind == "unreadable":
            entries.append([f"Deliverable folder {place} ({_services(f)}) cannot be read ({clip_line(f.error, NAME_SHOWN)})."])
        elif not f.name and f.kind == "link":
            entries.append([f"Deliverable folder {place} ({_services(f)}) is a link: not read (hirearchy reads only the folder the contract names)."])
        else:
            key = (f.folder, f.services)
            if key not in blocks:
                entries.append(key)
            blocks.setdefault(key, []).append(f)
    return "\n".join(line for entry in entries for line in (_block(entry, blocks[entry]) if isinstance(entry, tuple) else entry))
