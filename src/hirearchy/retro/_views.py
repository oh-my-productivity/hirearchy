"""The narrow views of the files that the signals read (design 7.7, 14.3): a signal's inputs decide what can nominate an item, so they are typed views
that hold human-tier verdicts, runtime facts (runs, times, the agents' tree) and root's own tasks, and no lessons, memory, notes or reports of a team."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OneOffCase:
    """One of root's one-off tasks as a case (a task root sent without a service, with its reworks): ``id`` is the head task's id, ``assignee`` who got it,
    ``title`` and ``goal`` (the first line of the head's ``## Goal``) are root's own words, ``criteria`` the lines of the head's ``## Acceptance criteria``
    section. ``judged`` is true when the user gave a human-tier verdict on it; ``runs`` are the runs it used (``runs_unknown`` says why they cannot be read)."""

    id: str
    assignee: str
    title: str
    criteria: tuple[str, ...] = ()
    goal: str = ""
    created: datetime | None = None
    judged: bool = False
    runs: int = 0
    runs_unknown: str = ""


@dataclass(frozen=True)
class AgentFact:
    """What the AGENT.md frontmatter of a live agent records of its creation (design 4.5): ``created``, ``hired_by``, ``approved_in`` (``plan {id}``,
    ``change {id}`` or ``""``) and ``kind``; ``plan_heading`` is true when its body holds the heading ``## Assignment (from the approved plan)`` that an
    older plan applier wrote; ``verifier`` is whether ``blueprint.is_verifier`` holds for it."""

    addr: str
    created: datetime | None
    hired_by: str
    approved_in: str
    kind: str = ""
    plan_heading: bool = False
    verifier: bool = False


@dataclass(frozen=True)
class RetiredFact:
    """A retired tree: ``retired`` (the record's time, else the tree's stamp), ``by``, ``reason`` and ``approved_in`` from its ``RETIRED.md``;
    ``recorded`` is false for a tree retired before Phase 2, which has no record."""

    addr: str
    retired: datetime | None
    by: str
    reason: str
    approved_in: str
    recorded: bool = True


@dataclass(frozen=True)
class ServiceFact:
    """A service defined: ``created`` and ``defined_by`` of its SERVICE.md v1, and the ``approved_in`` it records."""

    owner: str
    name: str
    created: datetime | None
    defined_by: str
    approved_in: str


@dataclass(frozen=True)
class ServiceRetired:
    """A retired copy of a service: the frontmatter of its ``RETIRED.md``."""

    owner: str
    name: str
    retired: datetime | None
    by: str
    reason: str
    approved_in: str


@dataclass(frozen=True)
class WriteFact:
    """A ``write`` tool call of the event log: when, by whom, on which path (design 4.5, the label ``by {parent}``)."""

    when: datetime
    actor: str
    path: str


@dataclass(frozen=True)
class EventFacts:
    """What the event log shows of the writes. ``covers_from`` is the time of its oldest event: a change made before it is beyond what the log can say;
    None when the log holds nothing (events off, or none yet)."""

    writes: tuple[WriteFact, ...] = ()
    covers_from: datetime | None = None
