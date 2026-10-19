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

from ..kernel import Message, msg_time

__all__ = [
    "Case",
    "CaseHistory",
    "ReflectionDigest",
    "ServicePromptSections",
    "ServiceReports",
    "Stats",
    "StatsReport",
    "Verdict",
    "lessons_of",
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

    @property
    def title(self) -> str:
        raise NotImplementedError  # red: C-reflection

    @property
    def feedback(self) -> Message | None:
        """The latest feedback note (the final verdict), None when the client has not rated the case."""
        raise NotImplementedError  # red: C-reflection

    @property
    def verdict(self) -> str | None:
        """The final verdict: that of the latest feedback."""
        raise NotImplementedError  # red: C-reflection

    @property
    def rejected(self) -> bool:
        """Was the case rejected at least once, whatever came after?"""
        raise NotImplementedError  # red: C-reflection

    @property
    def accepted_after_reject(self) -> bool:
        raise NotImplementedError  # red: C-reflection

    @property
    def evidence_at(self) -> datetime | None:
        """The latest moment this case produced evidence: its final result or its latest feedback."""
        raise NotImplementedError  # red: C-reflection


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
        raise NotImplementedError  # red: C-reflection

    @property
    def avg_runs(self) -> float | None:
        raise NotImplementedError  # red: C-reflection

    def line(self) -> str:
        raise NotImplementedError  # red: C-reflection


def summarize(items: Sequence[Case]) -> Stats:
    """Counts over cases: requests, done, failed, open (incl. blocked), reworked, average runs of finished, verdicts."""
    raise NotImplementedError  # red: C-reflection


def stats_by_version(items: Sequence[Case]) -> dict[int, Stats]:
    """:func:`summarize` per playbook version, grouped by the version in force when each case was first answered.

    (Not the version current when the request was sent: the owner typically revises the playbook right after the
    request arrives, and that request is then delivered under the new version.)
    """
    raise NotImplementedError  # red: C-reflection


def version_at(timeline: Sequence[tuple[int, datetime]], when: datetime | None) -> int:
    """The playbook version in force at ``when`` (None = now): the latest written at or before it; 0 if none yet."""
    raise NotImplementedError  # red: C-reflection


def lessons_of(result: Message) -> str:
    """The text of the ``## Lessons`` section of a result body ("" if there is none)."""
    raise NotImplementedError  # red: C-reflection


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

        ``case total: 19 runs used of 27 handed down (contract: 15 per request)``; when the chain was handed down more than the contract gives one
        request, it adds that the case exceeds the budget and that the user must be told. Empty for a task that is not a service request."""
        ...


@runtime_checkable
class ServicePromptSections(Protocol):
    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        """The sections of an owner's run prompt: its services, the playbook of each service it has an open request for, and (when the batch
        holds a new request, or the client's rejection of a delivery) what to reflect on first. Empty for an agent that owns no service.

        Each section starts and ends with a newline, to be appended after the notice and before "# New messages"."""
        ...
