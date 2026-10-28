"""The narrow views of the files that the signals read (design 7.7, 14.3): a signal's inputs decide what can nominate an item, so they are typed views
that hold human-tier verdicts, runtime facts (runs, times, the agents' tree) and root's own tasks, and no lessons, memory, notes or reports of a team."""

from __future__ import annotations

from collections.abc import Mapping
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
    owner: str = ""  # the service's owner, the rejection's message id, its task and the one question to ask the user about it: what the answer item's calls need
    rejection_id: str = ""
    task: str = ""
    question: str = ""


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
    idle_for: str = ""  # how long it has been idle, as ``fmt_duration`` words it (``2d``)


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


@dataclass(frozen=True)
class Occasion:
    """A case where a past change was exercised, or a later rejection or one-off task that bears on its target (4.4): the ``case``, the rejection ``ref`` (``""`` for
    a one-off task), when it happened and the ``tier`` of the verdict (only ``human`` counts)."""

    case: str
    ref: str = ""
    when: datetime | None = None
    tier: str = "human"


@dataclass(frozen=True)
class WatchState:
    """A playbook item's watch as Phase 1 states it: ``state``, the clean cases out of its own ``k``, and the rejections related to it."""

    state: str
    k: int
    clean: int
    related: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tracked:
    """A past change D7 weighs (4.4): ``kind`` is ``amendment``, ``playbook``, ``charter`` or ``structural``; ``has_target`` is false for a change that is the effect
    of no item and has no criterion of its own. ``exercised`` are the cases where it applied, ``recurred`` the later rejections (or one-off tasks of the same shape) on
    its target; ``watch`` is the item's Phase 1 state, for a playbook item."""

    text: str
    kind: str
    when: datetime | None
    has_target: bool = True
    exercised: tuple[Occasion, ...] = ()
    recurred: tuple[Occasion, ...] = ()
    watch: WatchState | None = None


@dataclass(frozen=True)
class FailedCase:
    """A judged case of a service that the user rejected (7.2): ``classes`` has the lineage class of each criterion a human rejection of it names (a pending rejection and
    a link to no criterion name none), ``signer`` signed its delivery off (``verifier``: it is a check), ``escape`` is true when that delivery was rejected, and
    ``rework_runs`` the runs of the owner's subtree after its first rejection (None when they cannot be read)."""

    case: str
    when: datetime | None
    classes: tuple[frozenset[str], ...]
    signer: str
    verifier: bool
    escape: bool
    rework_runs: int | None = None


@dataclass(frozen=True)
class TakenFix:
    """A ``checker-fix`` item that was taken (4.4): the verifier it instructed, the criterion it named, the item's id and the case in which the class recurred since
    (``""`` when it has not)."""

    verifier: str
    klass: str
    ref: str
    recurred_case: str = ""


@dataclass(frozen=True)
class OwnerFacts:
    """What the call that adds a checker to a service reads of its owner's team (runtime facts only): its direct reports and limits, its tools, the estimate of the
    team's runs now and the service's budget, the template of a check the team already has (``""`` for none) and the ``base_runs`` of the templates."""

    owner: str
    children: int
    max_children: int
    can_hire: bool
    tools: tuple[str, ...]
    team_estimate: int
    old_budget: int
    verifier_template: str = ""
    template_runs: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class ServiceFailures:
    """A service as 7.2 reads it: ``window`` has its failing cases among the last judged ones, ``judged`` the number of judged cases in that window, ``criteria`` the text
    of each current criterion, ``owner_facts`` the team and ``taken`` the instructions already taken."""

    service: str
    owner: str
    window: tuple[FailedCase, ...]
    judged: int
    criteria: Mapping[str, str]
    owner_facts: OwnerFacts
    taken: tuple[TakenFix, ...] = ()


@dataclass(frozen=True)
class EffectFacts:
    """What the files show after the last brief (4.5, "effect of an item"): the services defined by an extension (``owner/name``), the owners that got a checker from one, the
    ``agent|line_key`` of the lines in the added sections, the leads that got a worker, the retired agents, the agents whose runs were taken back, the criteria settled
    (``service/C``) and the rejections answered."""

    services: frozenset[str] = frozenset()
    checkers: frozenset[str] = frozenset()
    lines: frozenset[str] = frozenset()
    workers: frozenset[str] = frozenset()
    retired: frozenset[str] = frozenset()
    reclaimed: frozenset[str] = frozenset()
    clarified: frozenset[str] = frozenset()
    answered: frozenset[str] = frozenset()
