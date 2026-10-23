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
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import ROOT, JsonObject, Message, OrgError, strip_markers
from ._cap import playbook_word_cap

__all__ = [
    "Admission",
    "AmendmentBasis",
    "BASE_HEADING",
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
    "JUDGED_BYTES",
    "JudgedBase",
    "JudgedVersions",
    "LINKS_MAX",
    "LINK_HEADER",
    "Playbook",
    "REASON_MAX",
    "Rejection",
    "ServiceCatalog",
    "ServiceCommands",
    "ServiceEvidence",
    "ServiceHints",
    "ServiceStore",
    "VERDICTS",
    "changed_lines",
    "confirmed_amendments",
    "criteria_of",
    "line_key",
    "normalize_evidence",
    "normalize_links",
    "number_criteria",
    "playbook_word_cap",
    "quoting_lines",
    "repeats_rejection",
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
BASE_HEADING = "## Base: "  # the heading of the base section of a rework's task body (P4)
JUDGED_BYTES = 6000  # bytes of the judged versions a rework's task body carries, in all (P4)
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
    answers: str = ""  # the basis of this version: the rejection (its message id) it records the user's answer to; "" when it answers none
    about: str = ""  # ... the C<k> or R<k> id the user's question named (with ``answers``)
    words: str = ""  # ... the user's words, verbatim (with ``answers``, or with ``initiated``)
    initiated: str = ""  # ... "user": a change the user asked for on their own, outside any rejection; "" otherwise


@dataclass(frozen=True)
class Criterion:
    """One acceptance criterion of a contract, with its stable id ``C<k>`` (see :func:`number_criteria`)."""

    id: str  # "C<k>"
    text: str  # the criterion, verbatim
    since: int  # the contract version that first had it
    by: str  # who defined that version (its ``defined_by``): "root" for the user's seat
    current: bool  # it is in the latest version given to ``number_criteria``
    answers: str = ""  # the rejection (message id) the latest version that added the text answers; "" for a v1 text or an unanswered amendment
    user: bool = False  # the latest version that added the text was a change the user asked for on their own

    @property
    def amended(self) -> bool:
        """Added by an amendment of the human client: first seen in v2 or later, defined by root, still current. Rule (c) also needs the client's
        recorded yes: :func:`confirmed_amendments`."""
        return self.since >= 2 and self.by == ROOT and self.current


def number_criteria(
    versions: Sequence[tuple[int, str, Sequence[str]]], basis: Mapping[int, tuple[str, bool]] | None = None,
) -> list[Criterion]:
    """``(version, defined_by, acceptance)`` of every contract version, oldest first -> every criterion it ever had, by id (pure).

    The id of a criterion is fixed by the order in which its exact text first appeared: versions in the order given, each version's
    ``acceptance`` in list order, the first sight of a text takes ``C<k>``, ``k`` = 1 + the distinct texts seen before. Removing a criterion
    never renumbers the others, a reworded text is a new criterion, and a text that comes back keeps its first id.

    ``basis`` maps a version to ``(answers, user)``, the basis it records (``stored_basis``). A criterion carries the basis of the latest version
    that added its text (present in that version, absent from the one before): a text of v1 has none, and a version without an entry adds with none."""
    seen: dict[str, tuple[int, str]] = {}  # text -> (the version that first had it, who defined that version)
    added: dict[str, tuple[str, bool]] = {}  # text -> the basis of the latest version that added it
    before: set[str] = set()
    for version, defined_by, acceptance in versions:
        for text in acceptance:
            seen.setdefault(text, (version, defined_by))
            if version > 1 and text not in before:
                added[text] = (basis or {}).get(version, ("", False))
        before = set(acceptance)
    latest = set(versions[-1][2]) if versions else set()
    return [
        Criterion(f"C{k}", text, since, by, text in latest, *added.get(text, ("", False)))
        for k, (text, (since, by)) in enumerate(seen.items(), start=1)
    ]


def confirmed_amendments(criteria: Sequence[Criterion], confirmed: Collection[str]) -> list[Criterion]:
    """The criteria rule (c) admits, in the order given (pure): added by an amendment of the human client (``Criterion.amended``) and named by a
    link the client confirmed (``confirmed``: ``ServiceEvidence.confirmed``). It is the single definition of that eligibility."""
    return [c for c in criteria if c.amended and c.id in confirmed]


def criteria_of(numbered: Sequence[Criterion], texts: Sequence[str]) -> list[Criterion]:
    """The criteria with these texts, in the order of ``texts`` (a contract's acceptance list); a text ``numbered`` lacks is skipped."""
    by_text = {c.text: c for c in numbered}
    return [by_text[t] for t in texts if t in by_text]


def line_key(line: str) -> str:
    """The words of a playbook line, for comparing lines (pure): its letters and digits after its leading markdown markers, case-folded.

    Punctuation, spacing, list numbering (``3.`` -> ``4.`` when a step is inserted), bullets, checkboxes (``- [ ] x`` and ``- [x] x`` are the
    same line) and other markdown never make two lines differ; a change of any word, or of a number inside the text, does."""
    return "".join(ch for ch in strip_markers(line).casefold() if ch.isalnum())


def changed_lines(current: str, new: str) -> list[str]:
    """The lines of ``new`` (stripped, in order) whose :func:`line_key` is not among the keys of ``current``'s lines, counted as a multiset (a
    line repeated in ``new`` more often than in ``current`` counts once more); lines with an empty key (blank, ``---``, a fence, a lone ``-`` or
    ``#``) are never changes (pure). ``changed_lines(new, current)`` gives the removed lines."""
    have = Counter(key for line in current.splitlines() if (key := line_key(line)))
    out: list[str] = []
    for line in new.splitlines():
        key = line_key(line)
        if not key:
            continue
        if have[key] > 0:
            have[key] -= 1
        else:
            out.append(line.strip())
    return out


def _words(text: str) -> list[str]:
    return [word for word in re.split(r"[^0-9a-z]+", text.casefold()) if word]


def repeats_rejection(words: str, note: str) -> bool:
    """Do ``words`` (offered as the user's answer) repeat the rejection ``note`` they answer (pure)? True when their words are the same, or when
    the shorter of the two has at least 4 words and occurs as a contiguous run in the longer: symmetric, so a paste of the user's whole reject
    turn that contains the recorded note is caught as well as a part of the note. Fewer than 4 words: only equality counts (``"Yes, add it."``)."""
    a, b = _words(words), _words(note)
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 4 and any(long[i : i + len(short)] == short for i in range(len(long) - len(short) + 1))


def quoting_lines(body: str, criterion: Criterion) -> list[str]:
    """The lines of ``body`` (stripped, with a non-empty :func:`line_key`) that quote ``criterion`` (pure): they contain its id as a standalone
    token (``C9``, not ``C90`` or ``xC9``), or their key contains the key of its text, so the text quoted verbatim, modulo punctuation. A
    criterion whose text has no letter or digit has an empty key, which every line would "contain": it is matched by its id alone."""
    token = re.compile(rf"(?<![A-Za-z0-9]){re.escape(criterion.id)}(?![0-9])", re.IGNORECASE)
    text = line_key(criterion.text)
    return [
        stripped for line in body.splitlines()
        if (key := line_key(line)) and (stripped := line.strip()) and (token.search(line) or (text and text in key))
    ]


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
    evidence: list[str] = field(default_factory=list)  # the ids the owner cited for this version ([] for a legacy file or an exempt version)
    admitted: str = ""  # which rule admitted it: b | c | first | restore ("" for a legacy file; a version the client wrote has none)


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
        notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None, answers: str | None = None,
        about: str | None = None, words: str | None = None,
    ) -> str:
        """Define a service for ``owner`` (first definition), or amend its contract (the service exists). Returns a confirmation.

        Only ``owner``'s parent (root for a top-level agent) may call it: the contract is the client's. ``name`` is unique among the services of
        the owner's siblings. A first definition needs ``description``, ``acceptance``, ``deliverable`` and ``budget`` (``inputs`` default to none,
        ``locked`` to false) and writes ``SERVICE.md`` v1 (and ``PLAYBOOK.md`` v1 when ``playbook`` is given). On an existing service every field
        but ``owner`` and ``name`` is optional and an omitted (None) one keeps its value: ``add_acceptance`` appends criteria,
        ``remove_acceptance`` drops criteria (exact text), ``acceptance`` replaces them all (not with add/remove). The old contract is archived
        to ``history/SERVICE.v<n>.md``, ``n+1`` written, and the owner gets a non-waking note saying exactly what changed. A change that changes
        nothing is refused; ``playbook`` is refused (the owner's).

        Root's ``answers``, ``about`` and ``words`` record where an amendment of the acceptance criteria comes from (agents may not pass them): the
        user's answer to a rejection (``answers``: the rejection's message id; ``about``: the C or R id the question named; ``words``: their answer,
        verbatim), which also writes the ``confirms`` link, or, with ``words`` alone, a change they asked for on their own (user-initiated: it
        never admits a playbook revision). A rejection gets one answer.

        Root's definition of a name that has no live contract but a retired copy of the same owner with a recorded request (a request of it with a
        result of any status) continues that copy: it is restored, and the next contract version is written with the old ``created``, so the
        cases, the playbook and the criteria ids continue. Such a call cannot pass ``playbook`` or change the set of criteria."""
        ...

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        """Take a service out of use: it moves to ``<owner>/services/.retired/<name>-<timestamp>/``. Returns a confirmation.

        Same authority as ``define_service`` (the owner's parent). Afterwards the service is not listed and cannot be requested. Root retires a
        service only after every delivered request has a verdict and every rejection its answer (a refusal moves nothing). A service of the same
        name defined later for the same owner continues it (its contract, playbook and cases) when a request of it has a result of any status,
        and starts fresh otherwise. The owner is told in a non-waking note."""
        ...

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
        extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
        source: str | None = None, base: str | None = None,
    ) -> Message:
        """Ask one of ``actor``'s direct reports for its service ``service``: a task built from the contract.

        The task goes through the message sender like a delegation (same route, hops and budget rules, the reserve included). ``budget`` defaults
        to the contract's. ``extra_acceptance`` adds criteria after the contract's, which always travel unchanged. ``revises``: the id of an
        earlier request of this service to the same owner, to send it back. ``source`` (root only, with ``revises``): ``"human"`` when the user
        asked for the rework, ``"relayed"`` (the default of a root rework) when it is root's own reading. ``base`` (root only, with ``revises``
        and ``source="human"``): when a relayed rework changed an artifact after the delivery the client judged, the request is refused until it
        says which version the user's corrections apply to, ``"delivered"`` (the task then carries the judged text and the lead starts from it) or
        ``"latest"`` (the relayed changes stay); when none did, ``base`` is accepted and changes nothing. The task carries ``service``,
        ``contract`` and ``playbook`` (versions at this moment) in its frontmatter."""
        ...

    def revise_playbook(self, actor: str, service: str, content: str, reason: str, evidence: Sequence[str]) -> int:
        """Write the next version of the playbook of a service ``actor`` owns; returns the new version.

        Refused when the contract is locked, when ``content`` is empty, over ``playbook_max_words`` or identical to the current playbook. A
        frontmatter in ``content`` is stripped (the runtime writes it). The old version is archived to ``history/PLAYBOOK.v<n>.md`` and the client
        gets a quiet (non-waking) note with the reason, the evidence and the rule that admitted it.

        ``evidence`` (required; a list of at most 20 ids): what the revision rests on, ``R<k>`` regression assertions, ``C<k>`` criteria, verdict
        or case ids. The revision is admitted by ``ServiceEvidence``, by rule (b) the same criterion or assertion failed in 2 different cases
        the human client rejected, or rule (c) it cites a criterion the client added by an amendment and confirmed. Exempt, with ``[]``: the first
        playbook, and restoring unchanged a version the client wrote. A refusal writes nothing."""
        ...

    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
        """The client's verdict on a delivered service request: a quiet note to the owner (it costs no run).

        ``task_id``: any task of the case (the request or a rework) that ``actor`` sent and that has a result. ``verdict`` is ``accept`` or
        ``reject``; a rejection needs a ``note`` saying what was wrong. The owner sees it with its next batch and in the reflection digest. Every
        verdict stays in the case's history: the latest one is the final verdict of the statistics, and an earlier ``reject`` is still shown
        (and counted as "after a reject").

        Root only: ``source`` (``"human"``: the user's own judgement, in their words; ``"relayed"``, the default of a root verdict: anything root
        concluded itself), ``criterion`` (a rejection only: what it is about, as ids ``C<k>`` of the contract, ``R<k>`` of an earlier rejection
        it repeats, or ``none``: the client said it is no lasting rule) and ``confirms`` (the id of a rejection recorded on ``task_id``: ``criterion``
        is then recorded for it in a link note, which is no new verdict)."""
        ...


@dataclass(frozen=True)
class Admission:
    """Why a playbook revision may be written."""

    rule: str  # "b" | "c" | "first" | "restore"
    evidence: tuple[str, ...]  # the normalized ids cited
    detail: str  # one line for the client's note, e.g. "C6 failed in 2 cases the client rejected: <id>, <id>"
    lines: tuple[tuple[str, str], ...] = ()  # (the id that admits it, the line) of every line the revision added or changed; () when none/exempt


@dataclass(frozen=True)
class Rejection:
    """A rejection of a service request by the human client, with whether the user's answer to it is recorded (``ServiceEvidence.amendment_basis``)."""

    note: str  # the rejection's message id (its first 21 characters are when it was recorded)
    assertion: str  # its R<k> (service-wide numbering, as `services` shows it)
    task: str  # the request (or rework) it judged
    title: str  # that task's title (the link note's title names it)
    earlier: tuple[str, ...]  # the R ids recorded before it
    words: str  # the client's words in the rejection
    answered: str  # the id of the first human-tier link note that replies to it; "" while it has none
    question: str = ""  # the exact question to ask the user about it, with its ids filled in ("" until reflection words it)


@dataclass(frozen=True)
class AmendmentBasis:
    """What a root amendment of the acceptance criteria may answer."""

    rejections: tuple[Rejection, ...]  # every human-tier rejection of the service, oldest first
    unrated: tuple[str, ...]  # the latest task of every case whose delivery has no verdict yet


@runtime_checkable
class ServiceEvidence(Protocol):
    """What the history of a service proves: the ids a client's verdict may name, and whether a playbook revision is admitted."""

    def links(self, owner: str, service: str, ids: Sequence[str], *, verdict: str | None = None) -> tuple[str, ...]:
        """``ids`` (normalized: ``normalize_links``) if each is a criterion the contract has had (C<k>), an existing regression assertion (R<k>,
        not the rejection ``verdict`` itself) or ``none``; ``OrgError`` naming the unknown ones and listing the valid ones otherwise."""
        ...

    def admit(
        self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None, lines: Sequence[str] = (),
    ) -> Admission:
        """Judge a revision of ``owner``'s playbook by rules (b) and (c) of the evidence gate (rule (c): it cites a criterion the client added by
        an amendment and confirmed); ``exempt`` ("first", "restore"): only resolve the ids and return the exemption. ``lines`` are the lines the
        revision adds or changes (``changed_lines``): under rule (c) each must be the cited criterion's own words with its id, under rule (b) each
        must carry the id it rests on; the admission lists them with the id that admits each. ``OrgError`` with the client question when it is
        refused (an offending line included), or naming unknown ids."""
        ...

    def confirmed(self, owner: str, service: str) -> frozenset[str]:
        """The criterion ids of this service the human client confirmed with a link (``feedback(confirms=...)``); empty when there are none."""
        ...

    def amendment_basis(self, owner: str, service: str) -> AmendmentBasis:
        """What a root amendment of the acceptance criteria may answer: every human-tier rejection of the service (oldest first) with whether it has
        its answer, and the latest task of every case whose done delivery has no verdict yet. Empty for a service without cases."""
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


@dataclass(frozen=True)
class JudgedBase:
    """The delivery the client judged, and what relayed reworks changed after it (``JudgedVersions.base``)."""

    task: str  # the task whose delivery the client judged
    result: str  # that delivery (a result id)
    commit: str  # the org-git commit that holds it; "" without history
    relayed: tuple[str, ...]  # the relayed reworks of the case sent after it
    changed: tuple[str, ...]  # its artifacts (org paths) that differ now
    texts: tuple[tuple[str, str], ...]  # (path, judged text) of the changed artifacts included: at most ``JUDGED_BYTES`` bytes of UTF-8 in all


@runtime_checkable
class JudgedVersions(Protocol):
    def base(self, owner: str, service: str, revises: str) -> JudgedBase | None:
        """For a rework of ``revises``, a task of a case of ``owner``'s ``service``: the delivery the client judged (the latest human verdict's task and
        its result, else the latest ``done`` result of a task that was not relayed) and what relayed reworks sent after it changed in its artifacts.
        None when the task is in no case, nothing was judged or delivered, no relayed rework came after it, or none of its artifacts differs now: no
        base needs to be named."""
        ...
