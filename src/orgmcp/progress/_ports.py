"""The roles inside ``progress``: the narrow interfaces its classes depend on, and the small values they pass.

The providers (``MailboxReader``, ``AgentDirectory``, ``PauseStore``, ``RunnableQuery``, ``RunLogReader``, ``OrgLayout``, ``CaseHistory``, ``HumanQueue``, ...)
are the ports of the other packages; these are the parts a report is made of.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Protocol, runtime_checkable

from ..kernel import Message


class TaskState(NamedTuple):
    """The state of a root task (``working``, ``waiting on ceo/eng``, ``blocked: ...``, ``done`` ...) and who is busy (``running: ...; unread work: ...``)."""

    state: str
    who: str


class TaskMark(NamedTuple):
    """What a wait remembers of a task: the first word of its state (``kind``), its title and its whole state."""

    kind: str
    title: str
    state: str


@dataclass(frozen=True)
class Snapshot:
    """The listed tasks (id -> mark), what needs the user (message id -> line) and the tasks that have an agent below them that is running or can run now."""

    marks: Mapping[str, TaskMark]
    needs: Mapping[str, str]
    alive: frozenset[str]


@runtime_checkable
class TaskTeams(Protocol):
    def team_of(self, task: Message) -> list[str]:
        """The agents below the assignee, the assignee included (root never); empty when the assignee no longer exists."""
        ...


@runtime_checkable
class TaskStates(Protocol):
    def state_of(self, task: Message, result: Message | None, team: Sequence[str]) -> TaskState:
        """The state of a root task given its latest result and its team."""
        ...


@runtime_checkable
class RunCounts(Protocol):
    def runs_text(self, task: Message, result: Message | None, team: Sequence[str]) -> str:
        """``runs 3 of 8`` or ``runs 3 of 8 (5 returned)``: the runs the team made for the task against everything root put into it."""
        ...


@runtime_checkable
class TeamActivity(Protocol):
    def newest(self, team: Sequence[str]) -> datetime | None:
        """The newest message or run in the team's mailboxes and run logs; ``None`` when there is none."""
        ...


@runtime_checkable
class TeamLiveness(Protocol):
    def can_run(self, addr: str) -> bool:
        """Is ``addr`` running, or would a scheduler start it now (unread mail that wakes it, budget left, not paused)?"""
        ...

    def alive(self, team: Sequence[str]) -> bool:
        """Can any agent of the team run?"""
        ...


@runtime_checkable
class RootTasks(Protocol):
    def tasks(self) -> list[Message]:
        """The tasks root gave, oldest first."""
        ...

    def latest_results(self) -> dict[str, Message]:
        """The latest result of each task root gave, by task id."""
        ...


@runtime_checkable
class TaskLines(Protocol):
    def line(self, task: Message, result: Message | None, now: datetime) -> str:
        """The line of a task, ending in ``(task <id>)``."""
        ...


@runtime_checkable
class ProgressText(Protocol):
    def render(self, task_id: str | None, now: datetime | None) -> str:
        """The lines of the listed tasks (or of ``task_id``), then what needs the user."""
        ...


@runtime_checkable
class Snapshots(Protocol):
    def snapshot(self, task_id: str | None) -> Snapshot:
        """What a wait compares from look to look. Read-only."""
        ...


@runtime_checkable
class ProgressView(Protocol):
    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        """``ProgressReporter.progress``."""
        ...
