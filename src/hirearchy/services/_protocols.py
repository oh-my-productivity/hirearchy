"""The collaborators the rule classes of ``services`` use among themselves (package-private: nobody outside the package depends on them)."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import Message
from .api import Contract, Criterion, ItemWatch, JudgedBase, PlaybookChange


@runtime_checkable
class ServicePlaces(Protocol):
    """Where the files of a service are (path arithmetic only; nothing is read or written)."""

    def services_dir(self, owner: str) -> Path:
        """``<owner>/services``."""
        ...

    def service_dir(self, owner: str, name: str) -> Path:
        """``<owner>/services/<name>``."""
        ...

    def contract_file(self, owner: str, name: str) -> Path:
        """``SERVICE.md`` of the service."""
        ...

    def playbook_file(self, owner: str, name: str) -> Path:
        """``PLAYBOOK.md`` of the service."""
        ...

    def history_file(self, owner: str, name: str, kind: str, version: int) -> Path:
        """``history/<kind>.v<version>.md``, the kept version of ``SERVICE`` or ``PLAYBOOK``."""
        ...

    def retired_dir(self, owner: str, name: str, stamp: str) -> Path:
        """``services/.retired/<name>-<stamp>``."""
        ...

    def rel(self, path: Path) -> str:
        """``path`` relative to the organization, as text."""
        ...


@runtime_checkable
class OwnerAddresses(Protocol):
    def resolve(self, actor: str, owner: str) -> str:
        """``owner`` as a full address; a manager may give the short name of a direct report."""
        ...


@runtime_checkable
class PlaybookTexts(Protocol):
    def body(self, content: str | None) -> str:
        """The playbook body: the frontmatter (if the caller wrote one) stripped, non-empty, within the word cap; an ``OrgError`` otherwise."""
        ...

    def cap(self) -> int:
        """The most words a playbook may have: ``playbook_max_words`` of the settings (1000 when it is missing or malformed)."""
        ...


@runtime_checkable
class PlaybookWriter(Protocol):
    def write(
        self, owner: str, name: str, version: int, body: str, by: str, reason: str, archive_version: int | None = None,
        extra: Mapping[str, object] | None = None,
    ) -> str:
        """Write the playbook ``version`` (keeping ``archive_version`` of the old one when given) and say so in the event log. ``extra`` goes
        into the frontmatter after ``reason`` (``evidence``, ``admitted``, ``restores``); its ``admitted`` is also the ``admitted`` of the event
        (``"client"`` without it: a version the client wrote). Returns its path relative to the organization."""
        ...


@runtime_checkable
class ContractAmendment(Protocol):
    def listed(self, criteria: Sequence[Criterion], indent: str = "") -> str:
        """The criteria, one per line: ``{indent}{id}: {text}``."""
        ...

    def amended_criteria(self, name: str, current: Sequence[Criterion], add: object, remove: object) -> list[str]:
        """The texts of ``current`` without the ``remove`` criteria (exact text) and with the ``add`` ones appended; the errors say why not
        and list ``current`` with their ids."""
        ...

    def changes(self, old: Contract, new: Contract, ids: Mapping[str, str]) -> list[str]:
        """What differs between the old contract and the new one, one line each (criteria as ``{id}: {text}``, others old -> new);
        ``ids`` maps the text of every old and new criterion to its id."""
        ...

    def diff(
        self, old: Contract, new: Contract, changes: Sequence[str], where: str, criteria: Sequence[Criterion], confirmed: Collection[str],
        quoting: Mapping[str, Sequence[str]] | None = None, playbook_version: int = 0, by_item: bool = False,
    ) -> str:
        """The note to the owner: who changed the contract, exactly what, every current criterion with its id, and where to read it. A criterion
        added by an amendment whose id is not in ``confirmed`` (the client's recorded yes) ends ``(not confirmed)``. ``quoting`` maps a criterion
        the amendment removed to the lines of playbook v``playbook_version`` that quote it (with ``by_item``: to the ids of the items that cite it):
        each such criterion gets one advisory line."""
        ...


@runtime_checkable
class RequestBodies(Protocol):
    def body(
        self, contract: Contract, criteria: Sequence[Criterion], given: Mapping[str, str], extra: Sequence[str], note: str,
        base: tuple[str, JudgedBase | None] | None = None,
    ) -> str:
        """The body of a request: goal, the inputs given, the acceptance criteria (the contract's ``criteria`` with their ids, then ``extra``
        without), the deliverable, the note and, last, the base of a human rework (``base``: ``"delivered"`` or ``"latest"`` with what was found;
        no section when nothing was found)."""
        ...


@runtime_checkable
class ContractDefinitions(Protocol):
    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None, inputs: object, acceptance: object,
        deliverable: Mapping[str, object] | None, budget: int | None, playbook: str | None, locked: bool | None, notes: str | None,
        add_acceptance: object, remove_acceptance: object, answers: str | None, about: str | None, words: str | None,
    ) -> str:
        """Define or amend (see ``ServiceCommands.define_service``)."""
        ...


@runtime_checkable
class LinkNotes(Protocol):
    def write(self, actor: str, owner: str, title: str, rejection: str, ids: Sequence[str], words: str, source: str | None = "human") -> Message:
        """The link note on ``rejection`` (a message id): from ``actor`` (root) to ``owner``, ``LINK_HEADER`` and the user's ``words``, its
        ``criterion`` the ``ids``, title ``criterion link on "<title>": <ids>``, quiet (it wakes nobody). ``source`` is ``human``, the product's
        own link; ``feedback(confirms=...)`` passes the one its caller gave."""
        ...


@runtime_checkable
class ServiceRetirement(Protocol):
    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        """Take a service out of use (see ``ServiceCommands.retire_service``)."""
        ...


@runtime_checkable
class PlaybookRevisions(Protocol):
    def revise_playbook(
        self, actor: str, service: str, op: str | None, reason: str, evidence: Sequence[str], *, item: str | None = None, kind: str | None = None,
        text: str | None = None, when: str | None = None, then: str | None = None, after: str | None = None, version: int | None = None,
        acknowledged: str | None = None, content: str | None = None,
    ) -> PlaybookChange:
        """Change one item of a playbook (see ``ServiceCommands.revise_playbook``)."""
        ...


@runtime_checkable
class PlaybookAcknowledgements(Protocol):
    def acknowledge_playbook(
        self, actor: str, owner: str, service: str, item: str, op: str, *, text_hash: str | None = None, words: str | None = None,
    ) -> Message:
        """Write the parent's acknowledgement of a playbook change (see ``ServiceCommands.acknowledge_playbook``)."""
        ...


@dataclass(frozen=True)
class SettleReport:
    """What one settlement did (design 8.5): the ids it retired, the ids it warned, and the ``(id, error)`` of each retire (or note) it could not
    write (``""`` for the id when the watch itself could not be read)."""

    retired: tuple[str, ...] = ()
    warned: tuple[str, ...] = ()
    failed: tuple[tuple[str, str], ...] = ()


@runtime_checkable
class WatchSettlement(Protocol):
    def settle(self, owner: str, service: str, before: Sequence[ItemWatch] | None, *, strict: bool = False) -> SettleReport:
        """Retire what the watch says is due, in ``owner``'s ``service``: for every item with two related rejections, write the next playbook version
        without its watched text, the text before the watch back in its place when there is one, and tell the owner and the client (8.3). ``before`` is
        the watch as it stood before the write that may have changed it (None: not known, so no warning note is sent). A failed write is recorded in
        the report and never raised; with ``strict`` (the owner's op) a write that fails raises (``PlaybookRace`` against a concurrent writer)."""
        ...


@runtime_checkable
class ServiceRequests(Protocol):
    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str, note: str,
        extra_acceptance: Sequence[str] | None, budget: int | None, revises: str | None, source: str | None, base: str | None,
    ) -> Message:
        """Ask for a service (see ``ServiceCommands.request``)."""
        ...


@runtime_checkable
class ClientFeedback(Protocol):
    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
        """Give the verdict on a delivered request (see ``ServiceCommands.feedback``)."""
        ...


@dataclass(frozen=True)
class RetiredService:
    """A retired copy of a service that a root definition continues (design 5.10)."""

    path: str  # the copy, relative to the organization
    files: tuple[tuple[str, str], ...]  # (name inside the service directory, text): SERVICE.md, PLAYBOOK.md, history/SERVICE.v<k>.md, history/PLAYBOOK.v<k>.md
    recorded: int  # the requests of the service with a result of any status (done, blocked or failed)


@runtime_checkable
class ServiceFiles(Protocol):
    """The files of the copies the continuation reads (read only; nothing is written through it)."""

    def listdir(self, path: Path) -> list[str]:
        """The names in the directory ``path``; ``[]`` when there is no such directory (or it is a link); ``OSError`` when it cannot be listed."""
        ...

    def read_text(self, path: Path) -> str | None:
        """The text of the regular file ``path`` exactly as written (no newline translation); ``None`` when it is no regular file (nothing, a
        directory, a link); ``OSError`` when it cannot be read or decoded."""
        ...


@runtime_checkable
class ContinuedServices(Protocol):
    def continued(self, owner: str, name: str) -> RetiredService | None:
        """The retired copy a root definition of ``owner``'s ``name`` continues: the newest one, when a request of it has a result of any status
        (a recorded request); ``None`` otherwise. ``OSError``/``OrgError`` when a copy or a mailbox cannot be read."""
        ...


@runtime_checkable
class ServiceRestorer(Protocol):
    def restore(self, owner: str, name: str, retired: RetiredService) -> None:
        """Write the files of the copy byte for byte into the live service directory, ``SERVICE.md`` last. Only the four file shapes of a service
        are written; any other name is ignored."""
        ...
