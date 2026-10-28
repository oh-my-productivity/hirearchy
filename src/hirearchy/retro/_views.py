"""The narrow views of the files that the signals read (design 7.7, 14.3): a signal's inputs decide what can nominate an item, so they are typed views
that hold human-tier verdicts, runtime facts (runs, times, the agents' tree) and root's own tasks, and no lessons, memory, notes or reports of a team."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..reflection import CostAlarm, RepeatAlarm


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


@dataclass(frozen=True)
class Answering:
    """The contract version that answers a rejection (design 4.3 D1): its number and the criteria it adds and removes."""

    version: int
    adds: tuple[str, ...] = ()
    removes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Said:
    """One human rejection (D1, D3): ``service`` is ``""`` for one of root's one-off tasks, ``ref`` its ``R<k>``, ``words`` the user's own words. ``link`` is the
    state of its human link (``confirmed``, ``none``, ``unconfirmed`` or ``""``), ``about`` the criteria it names, ``same_as`` the earlier rejection it repeats,
    ``answering`` the contract version that answers it; ``current_about`` and ``removed_about`` split ``about`` into the criteria still in the contract and the ones removed."""

    service: str
    ref: str
    case: str
    when: datetime | None
    words: str
    link: str = ""
    about: tuple[str, ...] = ()
    same_as: str = ""
    answering: Answering | None = None
    current_about: tuple[str, ...] = ()
    removed_about: tuple[str, ...] = ()


@dataclass(frozen=True)
class Passed:
    """One escape (D2, D4): a delivery the team reported done and the user rejected. ``signer`` signed it off (``verifier``: ``blueprint.is_verifier`` holds
    for it), ``refs`` and ``criteria`` are the ids of the user's rejection and of the criteria its human link names, ``cause`` the type the rules gave it and
    ``also`` the other types a later rule matches (a disputed cause)."""

    service: str
    case: str
    delivery: str
    signer: str
    verifier: bool
    refs: tuple[str, ...]
    criteria: tuple[str, ...]
    cause: str
    also: tuple[str, ...]
    when: datetime | None
    words: str


@dataclass(frozen=True)
class ServiceAlarms:
    """The two alarms of a service's record (``reflection.RepeatAlarm`` and ``CostAlarm``, derived data: no team-written text)."""

    service: str
    repeat: RepeatAlarm
    cost: CostAlarm


@dataclass(frozen=True)
class HealthFlag:
    """An agent ``health`` flagged ``idle`` or ``stranded_budget`` with the analyzer's reason, and the unspent runs it holds (None when unknown)."""

    addr: str
    flag: str
    reason: str
    held: int | None = None


@dataclass(frozen=True)
class Sourced:
    """A current criterion with a recorded source (D9, 7.5): ``kind`` is ``user``, ``amendment``, ``default`` or ``tasks`` (never ``unknown``, which is only counted),
    ``quote`` the user's words it rests on, ``asked`` the question those words answered (for an amendment the id its question named), ``tasks_dates`` the dates of
    the one-off tasks it copies, ``added`` the words that are root's. ``exercised`` is the judged human cases it was exercised in, ``accepted`` how many were accepted."""

    service: str
    id: str
    text: str
    kind: str
    quote: str = ""
    asked: str = ""
    tasks_dates: str = ""
    added: tuple[str, ...] = ()
    exercised: int = 0
    accepted: int = 0


@dataclass(frozen=True)
class Refusal:
    """A refused ``revise_playbook`` call whose refusal is the evidence gate's (D10): who, on which service, which gate refusal (``reflection.gate_refusal_kind``)
    and the call's ``op``. No text of the team is kept."""

    actor: str
    service: str
    kind: str
    op: str


@dataclass(frozen=True)
class ProposalFacts:
    """D10's inputs: the gate refusals, the count of every refused tool call (the rule ``observe`` uses) and the count per tool."""

    rows: tuple[Refusal, ...] = ()
    refused: int = 0
    by_tool: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class WatchRetire:
    """A playbook item the watch retired (D11, 10.4): ``direct_refs`` are the rejections that named the criterion ``direct_criterion`` it carries,
    ``refined_refs`` those that named a refinement, and ``replaced`` the (old, new) criteria the answers replaced."""

    item: str
    version: int
    direct_refs: tuple[str, ...] = ()
    direct_criterion: str = ""
    refined_refs: tuple[str, ...] = ()
    replaced: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PlaybookFacts:
    """A service's playbook as D11 reads it: its words against the cap, its live items by watch state, the retire candidates, the mirror items (a live item whose
    tokens equal a current criterion's) with the words they repeat, and every watch retire."""

    service: str
    words: int
    cap: int
    states: tuple[tuple[str, int], ...] = ()
    candidates: tuple[str, ...] = ()
    mirrors: tuple[str, ...] = ()
    mirror_words: int = 0
    retires: tuple[WatchRetire, ...] = ()


@dataclass(frozen=True)
class SpendFacts:
    """D12: a service's cases since the window start, the runs they used, the runs approved per request and the cases above that."""

    service: str
    cases: int
    runs: int
    approved: int
    above: int


@dataclass(frozen=True)
class Fate:
    """What became of an item of the last brief (D13): ``state`` is ``taken`` (``seen`` is the effect found), ``lapsed`` or ``open``."""

    id: str
    kind: str
    state: str
    seen: str = ""
