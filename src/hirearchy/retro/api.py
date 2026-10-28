"""The public surface of ``retro``: the human's periodic retro brief, derived from the files (design 4).

The brief tells the user what the client said, what got past a check, whether each past change held, which structural changes happened and who made
them, and at most 3 numbered yes/no items, each with the one existing call its yes makes. Everything in it is DERIVED from files that exist: human-tier
verdicts, runtime facts (runs, budgets, times, the agents' tree), root's own tasks, the contracts and the committed charters. Nothing a team wrote nominates
an item. The one stored state is the ledger of the briefs held (``RetroRecords``, ``.runtime/retros.json``), needed because nothing else records when a
brief was held or what it offered.

``Brief``, ``Section``, ``Item`` and ``BriefRecord`` are the data; ``RetroThresholds`` the tunable defaults read from ORG.md's optional ``retro:`` mapping.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from fractions import Fraction
from types import MappingProxyType

__all__ = [
    "ASKED_KEPT",
    "Brief",
    "BriefRecord",
    "ITEMS_MAX",
    "ITEM_KINDS",
    "Item",
    "RECORDS_KEPT",
    "RETRO_DEFAULTS",
    "RecordedItem",
    "RetroThresholds",
    "Section",
    "retro_thresholds",
]

RECORDS_KEPT = 50  # the records the ledger keeps, the oldest dropped first (4.2)
ASKED_KEPT = 1000  # the item keys the ledger remembers, the oldest dropped first (4.2)
ITEMS_MAX = 3  # a brief has at most this many items (4.5a item 6)
ITEM_KINDS = ("answer", "cause", "clarify", "checker-fix", "service", "checker-add", "worker", "reclaim", "retire")  # in the order that breaks ties (4.5a item 5)

RETRO_DEFAULTS: Mapping[str, int | str] = MappingProxyType({
    "after_verdicts": 3, "window": 3, "carry": 3, "items": 3, "shape_cases": 3, "shape_overlap": "0.6", "criterion_cases": 3, "escapes": 2,
    "window_cases": 10, "saturation": "0.45", "added_words": 3, "accepted_cases": 3,
})


@dataclass(frozen=True)
class RetroThresholds:
    """The tunable thresholds of the brief (design 4.9); the defaults are ``RETRO_DEFAULTS``. ``retro_thresholds`` reads them. None of them comes from
    the literature or from a human organization: they are labelled defaults. ``source`` is ``defaults``, or ``ORG.md`` when at least one value came from
    its ``retro:`` mapping."""

    after_verdicts: int = 3  # the verdicts since the last brief at which a retro is due (4.6)
    window: int = 3  # the exercised cases at which a past change counts as having held (4.4)
    carry: int = 3  # the briefs back from which an inconclusive change is carried (4.4)
    items: int = 3  # the items a brief has at most (1, 2 or 3)
    shape_cases: int = 3  # the cases of one shape at which a service is suggested (7.1)
    shape_overlap: Fraction = Fraction("0.6")  # the Jaccard index at which two one-off tasks are of one shape (section 3)
    shape_overlap_text: str = "0.6"
    criterion_cases: int = 3  # the cases failing one lineage class at which a checker is suggested (7.2)
    escapes: int = 2  # the escapes on one verifier at which its instruction is suggested (7.2)
    window_cases: int = 10  # the judged cases a service's signals read (7.2, 7.3)
    saturation: Fraction = Fraction("0.45")  # the first-pass share below which a worker is suggested (7.3)
    saturation_text: str = "0.45"
    added_words: int = 3  # the words of its own a criterion has before clarify asks (7.5)
    accepted_cases: int = 3  # the accepted cases a criterion is exercised in before clarify asks (7.5)
    source: str = "defaults"


@dataclass(frozen=True)
class Item:
    """One numbered question of a brief (design 3, 4.5a). A candidate (what a signal returns) has ``n == 0``. ``kind`` is one of ``ITEM_KINDS``; ``key``
    the identity of its signal (kind, owner or service, and the shape or the class); ``evidence`` the case or rejection ids; ``weight`` the number of
    distinct cases of the evidence that carry a human-tier verdict; ``rung`` its place on the change ladder (1 to 7, 0 for an item that is no
    structure); ``question`` is the one sentence put to the user; ``call`` the pre-filled call its yes makes, ``revert`` the call that takes it back;
    ``objection`` the result of the objection test; ``effect`` what the files show once it is taken; ``notes`` the lines of Details beyond the fixed ones;
    ``state`` is ``""`` (new), ``taken``, ``open`` or ``no longer suggested``."""

    kind: str
    key: str
    evidence: tuple[str, ...]
    weight: int = 0
    rung: int = 0
    rung_why: str = ""
    question: str = ""
    call: str = ""
    revert: str = ""
    cost: str = ""
    objection: str = ""
    effect: Mapping[str, str] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    oldest: str = ""  # the lowest message id of the evidence: the third key of the order (4.5a item 5)
    n: int = 0
    state: str = ""


@dataclass(frozen=True)
class RecordedItem:
    """One item as the ledger keeps it (4.2): ids and keys only, never a client's words or a text the team wrote. ``lapsed`` counts how often an item
    with this key lapsed before."""

    n: int
    kind: str
    key: str
    evidence: tuple[str, ...] = ()
    effect: Mapping[str, str] = field(default_factory=dict)
    lapsed: int = 0


@dataclass(frozen=True)
class BriefRecord:
    """One held brief as the ledger keeps it (4.2): ``id`` (``B<n>``), ``at`` (when it was held), ``since`` (the start of its window; None for the
    organization's start when no date is known), ``by`` (``mcp`` or ``cli``), its ``items`` and the keys of the candidates it ``held_back``."""

    id: str
    at: datetime
    since: datetime | None
    by: str
    items: tuple[RecordedItem, ...] = ()
    held_back: tuple[str, ...] = ()


@dataclass(frozen=True)
class Section:
    """One section of a brief (design 4.3): ``key`` is ``d1`` to ``d15``. ``block`` holds the lines of its short form in the user's block (empty for
    a section the block does not show), ``details`` the lines of its full form; both are already capped (the block at 5 lines, 3 for the team's proposals,
    Details at 20). ``counts`` has every count of the section with its N, for the JSON; ``error`` is why the section could not be read ("" when it was)."""

    key: str
    heading: str
    block: tuple[str, ...] = ()
    details: tuple[str, ...] = ()
    counts: tuple[tuple[str, int | str], ...] = ()
    error: str = ""


@dataclass(frozen=True)
class Brief:
    """The result of one ``retro()`` call (design 3, 4.7). ``id`` is ``B<n>``, or ``look-back`` when ``since`` was given. ``since`` is the start of the
    window (None when the organization's start has no date) and ``since_words`` how the brief says so; ``verdicts`` and ``cases`` are the counts of its
    heading. ``items`` are at most 3, ``held_back`` the candidates beyond the cap. ``notes`` are the lines of 4.8 (an unreadable or an unwritable
    ledger) and of the thresholds. ``recorded`` is true when this call wrote the brief into the ledger; ``shown_again`` is the time of the last brief
    when this one is that brief shown again (nothing was recorded)."""

    id: str
    at: datetime
    since: datetime | None
    since_words: str
    verdicts: int = 0
    cases: int = 0
    sections: tuple[Section, ...] = ()
    items: tuple[Item, ...] = ()
    held_back: tuple[Item, ...] = ()
    notes: tuple[str, ...] = ()
    recorded: bool = False
    shown_again: str = ""


# Pure rules re-exported from their modules; they import the types above, so these imports come last.
from ._thresholds import retro_thresholds  # noqa: E402
