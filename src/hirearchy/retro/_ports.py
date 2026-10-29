"""The consumer port ``retro`` defines for the git history it reads (design 4.1, 4.5): the committed versions of the charters and of ORG.md.

``retro`` may not import ``snapshots``, so the composition root implements ``CharterHistory`` over ``snapshots.OrgHistory`` (``app/_charter_history.py``),
as it does ``reflection``'s ``BarHistory``. A pair carries what the files themselves say, so a label is read from content and never from a commit message.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ._facts import Facts
    from ._views import ServiceRetired

ORG = "ORG.md"
CHARTER = "AGENT.md"


@dataclass(frozen=True)
class KeyChange:
    """A frontmatter key whose value differs between two versions of a charter. A value is text: ``true``/``false`` for a boolean, ``null``, a number or
    a string as it reads, a list or mapping as sorted JSON; ``None`` when the key is not there."""

    key: str
    old: str | None
    new: str | None


@dataclass(frozen=True)
class CharterPair:
    """Two consecutive committed versions of ``<addr>/AGENT.md`` (or of ``ORG.md``), as the newer commit holds them. ``kind`` is ``edit`` (both exist),
    ``created`` (the older one does not exist: the first version at an address that had an earlier, retired agent) or ``deleted`` (the newer one does not
    exist: the tree was retired). An edit has ``keys`` (the frontmatter keys that differ, by key), ``added_before`` and ``added_after`` (the lines of the
    added section, stripped, blank lines left out) and ``body_differs`` (the body outside the added section differs). An ``ORG.md`` pair is listed only when
    its ``max_depth`` changed, and has ``depth`` (before, after) as text. ``when`` is the time of the newer commit, ``older`` that of the older one."""

    path: str
    commit: str
    when: datetime
    kind: str = "edit"
    keys: tuple[KeyChange, ...] = ()
    added_before: tuple[str, ...] = ()
    added_after: tuple[str, ...] = ()
    body_differs: bool = False
    depth: tuple[str, str] | None = None
    older: datetime | None = None  # the time of the older commit: the change happened between the two

    @property
    def addr(self) -> str:
        """The agent whose charter it is; ``""`` for ``ORG.md``."""
        return self.path.removesuffix(f"/{CHARTER}") if self.path != ORG else ""


@dataclass(frozen=True)
class CharterVersions:
    """The pairs ``CharterHistory.versions`` read, newest first. ``known`` is false without a history (no repository, no git): nothing is known and
    ``pairs`` is empty. ``truncated``: the list of commits was full or the time bound stopped the reading, so older changes may exist. ``skipped``: the
    versions not compared (too large, not UTF-8, frontmatter that does not parse), each counted once."""

    known: bool = False
    pairs: tuple[CharterPair, ...] = ()
    truncated: bool = False
    skipped: int = 0


@runtime_checkable
class CharterHistory(Protocol):
    def versions(self, addrs: Sequence[str]) -> CharterVersions:
        """The consecutive committed version pairs of ``<addr>/AGENT.md`` for ``addrs`` and of ``ORG.md`` (the ones whose ``max_depth`` changed), newest
        first: per pair the commit, its time, the frontmatter keys that differ (old and new value), the lines of the added section before and after,
        whether the body outside the added section differs, and for ORG.md the ``max_depth`` before and after. ``known`` is false without a history.
        Never raises; bounded (the newest 40 commits that changed one of the files, 5 s of git time), with ``truncated``."""
        ...

    def subject(self, commit: str) -> str | None:
        """The first line of the commit's message; None when it cannot be read. Never raises."""
        ...

    def org_started(self) -> datetime | None:
        """The commit time of the oldest commit that added ``ORG.md``; None without a history or when it cannot be found. Never raises."""
        ...


@runtime_checkable
class BriefSources(Protocol):
    """Where a brief's facts come from: the one place that reads the files (the services, the cases, the agents, the event log, health) and hands the brief its narrow views."""

    def started(self) -> datetime | None:
        """The organization's start: the earliest of root's oldest box entry, the oldest agent's ``created`` and the commit time of the oldest commit that added ORG.md;
        None when none of them gives a date. Never raises."""
        ...

    def new_verdicts(self, after: datetime | None) -> int:
        """The verdict count of 4.6: the deliveries (service and one-off) whose first counted human-tier verdict was created after ``after`` (all of them when None). A link
        note adds nothing to it. Never raises: a source that cannot be read counts 0."""
        ...

    def read(self, since: datetime | None, after: datetime | None) -> Facts:
        """The facts over the window that starts at ``since`` (None: the whole record). ``after`` is the time of the last brief (None before the first): the verdicts and the
        effects of its items are counted after it. A source that cannot be read becomes a line of ``Facts.unreadable``, not an exception; ``OrgError`` only when the agents
        cannot be listed."""
        ...


@runtime_checkable
class ServiceRetirements(Protocol):
    """The retired copies of services (``<owner>/services/.retired/<name>-<stamp>/RETIRED.md``): no public port of ``services`` lists them, so ``retro`` defines the one it needs
    and the composition root implements it (design 4.5, L22)."""

    def retired(self) -> tuple[ServiceRetired, ...]:
        """The record of every retired copy of a service: owner, name, when, by whom, why and the approval; a copy with no record is left out. Never raises."""
        ...
