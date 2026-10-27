"""The ports ``reflection`` defines for what it consumes (consumer-owned, narrower than the providers') and the roles inside the package.

The providers (``ServiceStore``, ``RunLogReader``, ``OrgSettings``, ``ServiceHints``, ``OrgLayout``) satisfy these structurally; the composition root
passes them. The last four are the parts the sections of the run prompt are made of.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..kernel import JsonObject, Message
from ..runs import RunLogFile
from ..services import Contract

if TYPE_CHECKING:  # the marks are defined in ``api``, which imports this module
    from .api import CharterMark, ModelMark


@runtime_checkable
class PlaybookHistory(Protocol):
    def playbook_history(self, owner: str, name: str) -> list[tuple[int, JsonObject]]:
        """``(version, frontmatter)`` of every playbook file of the service: the kept ones in ``history/``, then the current one."""
        ...


@runtime_checkable
class ContractVersions(Protocol):
    def versions(self, owner: str, name: str, kind: str) -> list[tuple[int, JsonObject, str]]:
        """``(version, frontmatter, body)`` of every stored file of ``kind`` (``"SERVICE"`` or ``"PLAYBOOK"``) of the service: the kept ones, then the
        current one, sorted by the version they state."""
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

    def stamps(self, team: Sequence[str], start: str, end: str | None) -> list[tuple[str, bool]]:
        """The 21-character stamps of the run logs of the agents of ``team`` in the same inclusive window, oldest first, one per log (two agents
        may share a stamp), each with whether a run credit in that agent's received box names the log (a credited run was not charged)."""
        ...


@runtime_checkable
class RejectedServices(Protocol):
    def among(self, addr: str, batch: Sequence[Message]) -> dict[str, str]:
        """The services of ``addr`` for which the batch holds a ``feedback: reject`` note (the client rejected a delivery), each with the strongest
        tier of its rejections: ``human``, else ``relayed``, else ``agent``."""
        ...


@runtime_checkable
class PlaybookSection(Protocol):
    def section(self, addr: str, contract: Contract, *, reflecting: bool = False) -> str:
        """The playbook of a service with an open request. ``reflecting``: the batch holds a new request and the prompt carries a "Reflect before
        you start" section (evidence to write the first playbook from)."""
        ...


@runtime_checkable
class ReflectSection(Protocol):
    def section(self, addr: str, contract: Contract, digest: Callable[[int], str], *, rejected: str = "", new_request: bool = True) -> str:
        """What to reflect on before the work starts, in at most 600 words with the digest of the evidence: ``digest(words)`` is the digest within
        ``words`` words, and the section asks for what its fixed text leaves. ``rejected``: the tier of the rejection that brings the section
        (``human``, ``relayed`` or ``agent``), ``""`` when there is none."""
        ...


@runtime_checkable
class RegressionSection(Protocol):
    def section(self, addr: str, contract: Contract) -> str:
        """The regression list of a service ``addr`` owns: the client's rejections, verbatim (the newest ones). ``""`` when it has none."""
        ...


@runtime_checkable
class ServicesListing(Protocol):
    def listing(self, addr: str, owned: Sequence[Contract]) -> str:
        """The opening of the prompt's services: who writes what, then one line per service ``addr`` owns (contract, playbook, requests so far, files)."""
        ...


# ------------------------------------------------------------------------------------------------------------------------ deliverable folders


@dataclass(frozen=True)
class Located:
    """The place a contract's ``deliverable.path`` names, before anything of it is opened."""

    target: Path  # absolute, normalized and resolved as it was when this was made
    named: Path  # absolute and normalized lexically: what the contract says
    link: bool = False  # the named path is itself a symbolic link


@dataclass(frozen=True)
class FolderFile:
    """One file of a deliverable folder, as read (the bytes never leave the process: the caller keeps their blob id)."""

    name: str
    kind: str  # "file" | "link" | "large" | "limit" | "unreadable"
    data: bytes = b""  # "file": the content (at most 4 MiB)
    mtime_us: int = 0  # the file's last write, in microseconds since the epoch
    error: str = ""  # "unreadable": the operating system's words for it (never the file's name)


@dataclass(frozen=True)
class FolderRead:
    """What reading a place gave: a folder (its direct files, sorted by name), one file, or why nothing was read."""

    state: str  # "folder" | "file" | "link" | "unreadable" | "missing"
    folder: str  # the folder read (a file: the folder it is in; a link: the place the contract names)
    files: tuple[FolderFile, ...] = ()
    error: str = ""  # "unreadable": the operating system's words for it
    used: int = 0  # bytes of content read, against the budget of one call


@runtime_checkable
class DeliverableFolder(Protocol):
    """The only way into a contract's deliverable folder (or file): nothing outside the place it names is opened."""

    def locate(self, raw: object) -> Located | None:
        """The place ``raw`` (a contract's ``deliverable.path``) names; None when it is not an absolute path."""
        ...

    def kind(self, place: Located) -> str:
        """What is there now: ``folder``, ``file``, ``link`` (the place, or a part of the way to it, is a link), ``unreadable`` (the folder cannot be
        opened) or ``missing``. Nothing is read."""
        ...

    def read(self, place: Located, budget: int) -> FolderRead:
        """The place, read: the direct files of a folder (at most 200, hidden ones left out) or the one file, at most 4 MiB each and ``budget``
        bytes in all. Never raises."""
        ...


@runtime_checkable
class CheckedVersions(Protocol):
    """What the team delivered, as git and the organization's files know it."""

    def at_result(self, result: Message, path: str) -> tuple[str, str] | None:
        """``(commit, blob id)`` of ``path`` (relative to the organization) at the first commit that holds ``result``'s sent copy; None when unknown."""
        ...

    def current(self, path: str, hexlen: int) -> str | None:
        """The blob id (``hexlen`` 40 or 64: the object format of the ids it is compared with) of the organization's file now; None when it is
        missing, not a regular file, larger than 4 MiB, or reached through a link or outside the organization."""
        ...

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        """The bytes of ``path`` at ``commit``; None when absent or larger than ``limit`` bytes."""
        ...


@runtime_checkable
class BlobIds(Protocol):
    def of(self, data: bytes, hexlen: int) -> str:
        """The git blob id of ``data`` in an object format of ``hexlen`` hex digits (40 or 64)."""
        ...


# ------------------------------------------------------------------------------------------------------------------------ the org's git history


@dataclass(frozen=True)
class BarChanges:
    """The changes of the bars (charters and models) the organization's git history shows. ``known`` is false without a history (no repository, no
    git): nothing is known, and the marks are empty."""

    known: bool = False
    marks: tuple[CharterMark | ModelMark, ...] = ()  # newest first within one file; the files in the order asked, ORG.md last
    truncated: bool = False  # the list of commits was full, or the time bound stopped the reading: older changes may exist
    skipped: int = 0  # versions that were not compared: above 64 KiB, unreadable, not UTF-8 or not parseable (each counted once)


@runtime_checkable
class BarHistory(Protocol):
    def changes(self, addrs: Sequence[str]) -> BarChanges:
        """The charter changes of the agents ``addrs`` (``<addr>/AGENT.md``: body edits, ``model`` changes) and the model settings of ORG.md
        (``default_model``, ``effort``) in the organization's history. Never raises."""
        ...
