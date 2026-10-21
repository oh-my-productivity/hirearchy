"""The collaborators the rule classes of ``services`` use among themselves (package-private: nobody outside the package depends on them)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import Message
from .api import Contract, Criterion


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


@runtime_checkable
class PlaybookWriter(Protocol):
    def write(self, owner: str, name: str, version: int, body: str, by: str, reason: str, archive_version: int | None = None) -> str:
        """Write the playbook ``version`` (keeping ``archive_version`` of the old one when given) and say so in the event log. Returns its path
        relative to the organization."""
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

    def diff(self, old: Contract, new: Contract, changes: Sequence[str], where: str, criteria: Sequence[Criterion]) -> str:
        """The note to the owner: who changed the contract, exactly what, every current criterion with its id, and where to read it."""
        ...


@runtime_checkable
class RequestBodies(Protocol):
    def body(self, contract: Contract, criteria: Sequence[Criterion], given: Mapping[str, str], extra: Sequence[str], note: str) -> str:
        """The body of a request: goal, the inputs given, the acceptance criteria (the contract's ``criteria`` with their ids, then ``extra``
        without), the deliverable, the note."""
        ...


@runtime_checkable
class ContractDefinitions(Protocol):
    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None, inputs: object, acceptance: object,
        deliverable: Mapping[str, object] | None, budget: int | None, playbook: str | None, locked: bool | None, notes: str | None,
        add_acceptance: object, remove_acceptance: object,
    ) -> str:
        """Define or amend (see ``ServiceCommands.define_service``)."""
        ...


@runtime_checkable
class ServiceRetirement(Protocol):
    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        """Take a service out of use (see ``ServiceCommands.retire_service``)."""
        ...


@runtime_checkable
class PlaybookRevisions(Protocol):
    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        """Write the next version of a playbook (see ``ServiceCommands.revise_playbook``)."""
        ...


@runtime_checkable
class ServiceRequests(Protocol):
    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str, note: str,
        extra_acceptance: Sequence[str] | None, budget: int | None, revises: str | None, source: str | None,
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
