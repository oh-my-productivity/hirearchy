"""The ports ``reflection`` defines for what it consumes (consumer-owned, narrower than the providers') and the roles inside the package.

The providers (``ServiceStore``, ``RunLogReader``, ``OrgSettings``, ``ServiceHints``, ``OrgLayout``) satisfy these structurally; the composition root
passes them. The last three are the parts the sections of the run prompt are made of.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, Message
from ..runs import RunLogFile
from ..services import Contract


@runtime_checkable
class PlaybookHistory(Protocol):
    def playbook_history(self, owner: str, name: str) -> list[tuple[int, JsonObject]]:
        """``(version, frontmatter)`` of every playbook file of the service: the kept ones in ``history/``, then the current one."""
        ...


@runtime_checkable
class FeedbackWords(Protocol):
    def feedback_text(self, msg: Message) -> str:
        """The client's own words in a feedback note (``""`` for a bare accept); the fixed header is not part of them."""
        ...


@runtime_checkable
class RunLogNames(Protocol):
    def files(self, addr: str) -> list[RunLogFile]:
        """The visible run logs of the agent, oldest first (by name)."""
        ...


@runtime_checkable
class ConfigSource(Protocol):
    def config(self) -> JsonObject:
        """The settings of ORG.md (its frontmatter over the defaults)."""
        ...


@runtime_checkable
class ServicePaths(Protocol):
    def rel(self, path: Path | None) -> str:
        """``path`` relative to the organization as text; ``""`` for none."""
        ...

    def service_dir(self, owner: str, name: str) -> str:
        """``<owner>/services/<name>``, relative to the organization."""
        ...

    def playbook_file(self, owner: str, name: str) -> str:
        """``<owner>/services/<name>/PLAYBOOK.md``, relative to the organization."""
        ...


@runtime_checkable
class PlaybookTimelines(Protocol):
    def timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        """(version, when it was written) of every playbook version the service has had, oldest first."""
        ...


@runtime_checkable
class RunCounter(Protocol):
    def runs_between(self, team: Sequence[str], start: str, end: str | None) -> int:
        """The run logs of the agents of ``team`` whose name (its first 21 characters) is at or after ``start`` and, when ``end`` is given, at or
        before it."""
        ...


@runtime_checkable
class RejectedServices(Protocol):
    def among(self, addr: str, batch: Sequence[Message]) -> set[str]:
        """The services of ``addr`` for which the batch holds a ``feedback: reject`` note (the client rejected a delivery)."""
        ...


@runtime_checkable
class PlaybookSection(Protocol):
    def section(self, addr: str, contract: Contract, *, reflecting: bool = False) -> str:
        """The playbook of a service with an open request. ``reflecting``: the batch holds a new request and the prompt carries a "Reflect before
        you start" section (evidence to write the first playbook from)."""
        ...


@runtime_checkable
class ReflectSection(Protocol):
    def section(self, addr: str, contract: Contract, digest: str, *, rejected: bool = False, new_request: bool = True) -> str:
        """What to reflect on before the work starts, with the digest of the evidence."""
        ...
