"""The public surface of ``services``: standing services, each with a contract, a playbook, requests and the client's feedback.

A *service* is a standing offer by one agent (the owner, usually a team lead) to do one kind of task on request:

* the **contract** ``<owner>/services/<name>/SERVICE.md`` is the client's (the owner's parent): what may be asked, the acceptance criteria, the budget of
  a request. The owner cannot change it, so improving the playbook can never lower the bar;
* the **playbook** ``PLAYBOOK.md`` (how the team does it) is written by the owner and versioned by the runtime;
* a **request** is a task built from the contract, so every rule of tasks applies unchanged; the client's **feedback** is a quiet note to the owner.

``ServiceStore`` is the files, ``ServiceCatalog`` reads the contracts and playbooks, ``ServiceCommands`` changes them and makes requests and feedback,
``ServiceHints`` is what the ``report`` tool adds for a request, ``ContractNormalizer`` turns the free input of a contract into its fixed form. The
derived history of the requests (cases, statistics, the reflection digest) is not here: it belongs to ``reflection``.

Files::

    <owner>/services/<name>/SERVICE.md, PLAYBOOK.md, history/SERVICE.v<n>.md, history/PLAYBOOK.v<n>.md
    <owner>/services/.retired/<name>-<timestamp>/   (retired services)
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import ROOT, JsonObject, Message, OrgError
from ._cap import playbook_word_cap

__all__ = [
    "Admission",
    "Contract",
    "ContractNormalizer",
    "Criterion",
    "DELIVERABLE_KEYS",
    "DESCRIPTION_MAX",
    "EVIDENCE_ID_MAX",
    "EVIDENCE_MAX",
    "FEEDBACK_HEADER",
    "FEEDBACK_MAX",
    "INPUT_RE",
    "LINKS_MAX",
    "LINK_HEADER",
    "Playbook",
    "REASON_MAX",
    "ServiceCatalog",
    "ServiceCommands",
    "ServiceEvidence",
    "ServiceHints",
    "ServiceStore",
    "VERDICTS",
    "criteria_of",
    "normalize_evidence",
    "normalize_links",
    "number_criteria",
    "playbook_word_cap",
]

INPUT_RE = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
VERDICTS = ("accept", "reject")
DESCRIPTION_MAX = 300
REASON_MAX = 400
FEEDBACK_MAX = 1000
DELIVERABLE_KEYS = ("description", "format", "max_words", "path")
FEEDBACK_HEADER = (
    "Client feedback for reflection only: it does not change this task's acceptance criteria or outcome; "
    "report `done` only if every criterion is met."
)
LINK_HEADER = (
    "The client says what their rejection {confirms} was about, for reflection only: it does not change any task's acceptance criteria or outcome."
)
EVIDENCE_MAX = 20  # ids a playbook revision may cite
EVIDENCE_ID_MAX = 80  # characters of one cited id
LINKS_MAX = 5  # ids one rejection may name as what it is about
_REF_RE = re.compile(r"[cr]\d+\Z", re.IGNORECASE)  # C<k> and R<k>, in either case
_LINK_RE = re.compile(r"[CR]\d+\Z")
_EVIDENCE_ERROR = (
    f"evidence is a list of at most {EVIDENCE_MAX} ids, each 1-{EVIDENCE_ID_MAX} characters without spaces: the regression assertions (R<k>), "
    "criteria (C<k>), verdict ids and case ids this revision rests on (see the regression list and the digest in your prompt). Pass [] only for "
    "the first playbook, or to restore unchanged a version your parent wrote."
)
_LINKS_ERROR = (
    f"criterion is 1-{LINKS_MAX} ids: C<k> (a criterion of the contract, see `services`), R<k> (an earlier rejection this one repeats) or none "
    '(the client said there is no lasting rule), e.g. ["C6"]. Not understood: {items}'
)
_NONE_ALONE = "none stands alone: it records that the client said this rejection is no lasting rule."


@dataclass
class Contract:
    """A parsed ``SERVICE.md``."""

    name: str
    owner: str
    description: str = ""
    inputs: list[JsonObject] = field(default_factory=list)  # {"name", "description", "required"}
    acceptance: list[str] = field(default_factory=list)
    deliverable: JsonObject = field(default_factory=dict)
    budget: int = 1
    locked: bool = False
    version: int = 1
    defined_by: str = ""
    defined: datetime | None = None
    created: datetime | None = None  # when the service was first defined (requests before it belong to an older service)
    notes: str = ""  # free text body: notes from the client
    path: Path | None = None


@dataclass(frozen=True)
class Criterion:
    """One acceptance criterion of a contract, with its stable id ``C<k>`` (see :func:`number_criteria`)."""

    id: str  # "C<k>"
    text: str  # the criterion, verbatim
    since: int  # the contract version that first had it
    by: str  # who defined that version (its ``defined_by``): "root" for the user's seat
    current: bool  # it is in the latest version given to ``number_criteria``

    @property
    def amended(self) -> bool:
        """Added by an amendment of the human client: first seen in v2 or later, defined by root, still current."""
        return self.since >= 2 and self.by == ROOT and self.current


def number_criteria(versions: Sequence[tuple[int, str, Sequence[str]]]) -> list[Criterion]:
    """``(version, defined_by, acceptance)`` of every contract version, oldest first -> every criterion it ever had, by id (pure).

    The id of a criterion is fixed by the order in which its exact text first appeared: versions in the order given, each version's
    ``acceptance`` in list order, the first sight of a text takes ``C<k>``, ``k`` = 1 + the distinct texts seen before. Removing a criterion
    never renumbers the others, a reworded text is a new criterion, and a text that comes back keeps its first id."""
    seen: dict[str, tuple[int, str]] = {}  # text -> (the version that first had it, who defined that version)
    for version, defined_by, acceptance in versions:
        for text in acceptance:
            seen.setdefault(text, (version, defined_by))
    latest = set(versions[-1][2]) if versions else set()
    return [Criterion(f"C{k}", text, since, by, text in latest) for k, (text, (since, by)) in enumerate(seen.items(), start=1)]


def criteria_of(numbered: Sequence[Criterion], texts: Sequence[str]) -> list[Criterion]:
    """The criteria with these texts, in the order of ``texts`` (a contract's acceptance list); a text ``numbered`` lacks is skipped."""
    by_text = {c.text: c for c in numbered}
    return [by_text[t] for t in texts if t in by_text]


def normalize_evidence(ids: object) -> tuple[str, ...]:
    """The ids a playbook revision cites, in their fixed form: each stripped, blanks and duplicates dropped, ``c<k>``/``r<k>`` upper-cased.

    A list (or tuple) of at most ``EVIDENCE_MAX`` strings, each of at most ``EVIDENCE_ID_MAX`` characters without whitespace; anything else is
    an ``OrgError`` (P1)."""
    if not isinstance(ids, (list, tuple)) or len(ids) > EVIDENCE_MAX or not all(isinstance(x, str) for x in ids):
        raise OrgError(_EVIDENCE_ERROR)
    out: list[str] = []
    for raw in ids:
        x = raw.strip()
        if len(x) > EVIDENCE_ID_MAX or any(c.isspace() for c in x):
            raise OrgError(_EVIDENCE_ERROR)
        if x:
            x = x.upper() if _REF_RE.match(x) else x
            if x not in out:
                out.append(x)
    return tuple(out)


def normalize_links(ids: object) -> tuple[str, ...]:
    """What a rejection says it is about, in its fixed form: each id stripped, ``c<k>``/``r<k>`` upper-cased, ``none`` lower-cased, blanks and
    duplicates dropped; nothing (None, an empty list) gives ``()``. The shape checks only (whether the ids exist is ``ServiceEvidence.links``'):
    more than ``LINKS_MAX`` ids, or one that is none of ``C<k>``, ``R<k>``, ``none`` is an ``OrgError`` (F3); ``none`` with another id (F4)."""
    if ids is None:
        return ()
    if not isinstance(ids, (list, tuple)):
        raise OrgError(_LINKS_ERROR.format(items=ids))
    out: list[str] = []
    for raw in ids:
        x = str(raw).strip()
        x = "none" if x.lower() == "none" else x.upper() if _REF_RE.match(x) else x
        if x and x not in out:
            out.append(x)
    unknown = [x for x in out if x != "none" and not _LINK_RE.match(x)]
    if unknown or len(out) > LINKS_MAX:
        raise OrgError(_LINKS_ERROR.format(items=", ".join(unknown or out[LINKS_MAX:])))
    if "none" in out and len(out) > 1:
        raise OrgError(_NONE_ALONE)
    return tuple(out)


@dataclass
class Playbook:
    """A parsed ``PLAYBOOK.md``; ``version`` 0 = there is none."""

    version: int = 0
    revised: datetime | None = None
    by: str = ""
    reason: str = ""
    body: str = ""
    path: Path | None = None


@runtime_checkable
class ServiceStore(Protocol):
    """The files of one owner's services (the only writer of ``<owner>/services/**``)."""

    def names(self, owner: str) -> list[str]:
        """The directories of ``<owner>/services`` that hold a ``SERVICE.md``, sorted, without the hidden ones (``.retired``)."""
        ...

    def read_contract(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        """``(frontmatter, body)`` of ``SERVICE.md``, or None when there is none."""
        ...

    def read_playbook(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        """``(frontmatter, body)`` of ``PLAYBOOK.md``, or None when there is none."""
        ...

    def write_contract(self, owner: str, name: str, meta: JsonObject, body: str, archive_version: int | None) -> str:
        """Write ``SERVICE.md``; first the current one is kept as ``history/SERVICE.v<archive_version>.md`` when ``archive_version`` is given.
        Returns the path of ``SERVICE.md`` relative to the organization."""
        ...

    def write_playbook(
        self, owner: str, name: str, version: int, meta: JsonObject, body: str, archive_version: int | None = None,
    ) -> str:
        """Write ``PLAYBOOK.md`` (``version`` is the one in ``meta``); first the current one is kept as ``history/PLAYBOOK.v<archive_version>.md``
        when ``archive_version`` is given. Returns the path of ``PLAYBOOK.md`` relative to the organization."""
        ...

    def retire(self, owner: str, name: str, stamp: str) -> str:
        """Move the service to ``<owner>/services/.retired/<name>-<stamp>``; returns that directory relative to the organization."""
        ...

    def playbook_history(self, owner: str, name: str) -> list[tuple[int, JsonObject]]:
        """``(version, frontmatter)`` of every playbook file of the service: the kept ones in ``history/`` (by file name), then the current one.
        The version is the one the frontmatter says (0 when it says none)."""
        ...

    def versions(self, owner: str, name: str, kind: str) -> list[tuple[int, JsonObject, str]]:
        """``(version, frontmatter, body)`` of every file of ``kind`` (``"SERVICE"`` or ``"PLAYBOOK"``, otherwise ``ValueError``): the kept ones
        in ``history/``, then the current one, sorted by the version the frontmatter states (0 when it states none). When two files state one
        version, the current file wins. Files that are missing are skipped."""
        ...


@runtime_checkable
class ServiceCatalog(Protocol):
    def service_names(self, addr: str) -> list[str]:
        """The (non-retired) services ``addr`` offers, by name; root offers none."""
        ...

    def read_contract(self, owner: str, name: str) -> Contract | None:
        """The contract of ``owner``'s service ``name``; None when there is no such (non-retired) service."""
        ...

    def read_playbook(self, owner: str, name: str) -> Playbook:
        """The current playbook of a service (version 0 when it has none yet)."""
        ...

    def owned_services(self, owner: str) -> list[Contract]:
        """The services ``owner`` offers (not the retired ones), by name."""
        ...

    def requestable_services(self, actor: str) -> list[Contract]:
        """The services ``actor`` can request: those of its direct reports (root: of its top-level agents)."""
        ...

    def criteria(self, owner: str, name: str) -> list[Criterion]:
        """Every criterion the contract of this service ever had, by id, from the versions that are kept (empty when there is no such service)."""
        ...

    def playbook_versions(self, owner: str, name: str) -> list[Playbook]:
        """Every playbook version that is kept, oldest first, the current one last (empty when there is none)."""
        ...


@runtime_checkable
class ServiceCommands(Protocol):
    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs: object = None, acceptance: object = None,
        deliverable: Mapping[str, object] | None = None, budget: int | None = None, playbook: str | None = None, locked: bool | None = None,
        notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None,
    ) -> str:
        """Define a service for ``owner`` (first definition), or amend its contract (the service exists). Returns a confirmation.

        Only ``owner``'s parent (root for a top-level agent) may call it: the contract is the client's. ``name`` is unique among the services of
        the owner's siblings. A first definition needs ``description``, ``acceptance``, ``deliverable`` and ``budget`` (``inputs`` default to none,
        ``locked`` to false) and writes ``SERVICE.md`` v1 (and ``PLAYBOOK.md`` v1 when ``playbook`` is given). On an existing service every field
        but ``owner`` and ``name`` is optional and an omitted (None) one keeps its value: ``add_acceptance`` appends criteria,
        ``remove_acceptance`` drops criteria (exact text), ``acceptance`` replaces them all (not with add/remove). The old contract is archived
        to ``history/SERVICE.v<n>.md``, ``n+1`` written, and the owner gets a non-waking note saying exactly what changed. A change that changes
        nothing is refused; ``playbook`` is refused (the owner's)."""
        ...

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        """Take a service out of use: it moves to ``<owner>/services/.retired/<name>-<timestamp>/``. Returns a confirmation.

        Same authority as ``define_service`` (the owner's parent). Afterwards the service is not listed and cannot be requested; its past cases no
        longer count for a service of the same name defined later. The owner is told in a non-waking note."""
        ...

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
        extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
        source: str | None = None,
    ) -> Message:
        """Ask one of ``actor``'s direct reports for its service ``service``: a task built from the contract.

        The task goes through the message sender like a delegation (same route, hops and budget rules, the reserve included). ``budget`` defaults
        to the contract's. ``extra_acceptance`` adds criteria after the contract's, which always travel unchanged. ``revises``: the id of an
        earlier request of this service to the same owner, to send it back. ``source`` (root only, with ``revises``): ``"human"`` when the user
        asked for the rework, ``"relayed"`` (the default of a root rework) when it is root's own reading. The task carries ``service``,
        ``contract`` and ``playbook`` (versions at this moment) in its frontmatter."""
        ...

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        """Write the next version of the playbook of a service ``actor`` owns; returns the new version.

        Refused when the contract is locked, when ``content`` is empty, over ``playbook_max_words`` or identical to the current playbook. A
        frontmatter in ``content`` is stripped (the runtime writes it). The old version is archived to ``history/PLAYBOOK.v<n>.md`` and the client
        gets a quiet (non-waking) note with the reason."""
        ...

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        """The client's verdict on a delivered service request: a quiet note to the owner (it costs no run).

        ``task_id``: any task of the case (the request or a rework) that ``actor`` sent and that has a result. ``verdict`` is ``accept`` or
        ``reject``; a rejection needs a ``note`` saying what was wrong. The owner sees it with its next batch and in the reflection digest. Every
        verdict stays in the case's history: the latest one is the final verdict of the statistics, and an earlier ``reject`` is still shown
        (and counted as "after a reject")."""
        ...


@dataclass(frozen=True)
class Admission:
    """Why a playbook revision may be written."""

    rule: str  # "b" | "c" | "first" | "restore"
    evidence: tuple[str, ...]  # the normalized ids cited
    detail: str  # one line for the client's note, e.g. "C6 failed in 2 cases the client rejected: <id>, <id>"


@runtime_checkable
class ServiceEvidence(Protocol):
    """What the history of a service proves: the ids a client's verdict may name, and whether a playbook revision is admitted."""

    def links(self, owner: str, service: str, ids: Sequence[str], *, verdict: str | None = None) -> tuple[str, ...]:
        """``ids`` (normalized: ``normalize_links``) if each is a criterion the contract has had (C<k>), an existing regression assertion (R<k>,
        not the rejection ``verdict`` itself) or ``none``; ``OrgError`` naming the unknown ones and listing the valid ones otherwise."""
        ...

    def admit(self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None) -> Admission:
        """Judge a revision of ``owner``'s playbook by rules (b) and (c) of the evidence gate; ``exempt`` ("first", "restore"): only resolve
        the ids and return the exemption. ``OrgError`` with the client question when it is refused, or naming unknown ids."""
        ...


@runtime_checkable
class ServiceHints(Protocol):
    def report_hint(self, actor: str, task: Message, status: str) -> str:
        """What the ``report`` tool adds to its reply for a final result on a service request (empty otherwise)."""
        ...

    def feedback_text(self, msg: Message) -> str:
        """The client's own words in a feedback note (``""`` for a bare accept); the fixed header is not part of them."""
        ...


@runtime_checkable
class ContractNormalizer(Protocol):
    def parse_input_spec(self, spec: str) -> JsonObject:
        """``'topic*:what it is about'`` -> ``{"name": "topic", "description": "what it is about", "required": True}``. A trailing ``*`` on the name
        marks it required; without it the input is optional."""
        ...

    def inputs(self, value: object) -> list[JsonObject]:
        """The inputs of a contract in their fixed form (``name``, ``description``, ``required``); an ``OrgError`` says what is wrong."""
        ...

    def deliverable(self, value: object) -> JsonObject:
        """The deliverable of a contract in its fixed form (``description``, and ``format``, ``max_words``, ``path`` when given)."""
        ...
