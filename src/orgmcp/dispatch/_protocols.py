"""The collaborators the rule classes of ``dispatch`` use among themselves (package-private: nobody outside the package depends on them)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import Message


@runtime_checkable
class RoutePolicy(Protocol):
    def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
        """May ``sender`` message ``to``? The human and the runtime may message anyone; nobody may message itself; an agent may message its
        parent, its direct reports and its siblings, and, with ``reply_to``, whoever sent it that message."""
        ...


@runtime_checkable
class HopCounter(Protocol):
    def next_hops(self, actor: str) -> int:
        """The ``hops`` of a message ``actor`` sends now: 0 for the human and the runtime, else one more than the longest chain among the
        messages in its current batch."""
        ...


@runtime_checkable
class ArtifactNormalizer(Protocol):
    def normalize(self, actor: str, path: str, since: str = "") -> str:
        """An artifact path of a report as the manager is shown it: where it is, and what a manager can check a claim against (its size in
        words and its modification time, and ``NOT modified since this task was assigned`` when it is older than ``since``). ``OrgError``
        for a path outside the organization and the reporter's workspace, and for one that does not exist."""
        ...


@runtime_checkable
class LessonsCheck(Protocol):
    def check(self, task: Message, status: str, lessons: str | None) -> str:
        """The lessons text of a report: required on a request for a service (done, failed or blocked), at most ``LESSONS_MAX_CHARS``."""
        ...
