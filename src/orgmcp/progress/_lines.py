"""The line of a root task (moved from ``progress._task_line``, ``_rated`` and ``_artifacts``)."""

from __future__ import annotations

from datetime import datetime

from ..kernel import Message
from ..reflection import Case, CaseHistory, ServiceReports
from ._ports import RunCounts, TaskLines, TaskStates, TaskTeams, TeamActivity


def artifacts_of(result: Message) -> list[str]:
    """Paths listed under ``## Artifacts`` (the runtime's word-count notes after the path are dropped)."""
    raise NotImplementedError("red: C-progress")


def rated(case: Case | None, task: Message) -> bool:
    """Has the client given feedback on this delivery (or on a later rework of it)? An earlier verdict does not count."""
    raise NotImplementedError("red: C-progress")


class CaseTaskLines(TaskLines):
    def __init__(
        self, teams: TaskTeams, states: TaskStates, runs: RunCounts, activity: TeamActivity, history: CaseHistory, reports: ServiceReports,
    ) -> None:
        self._teams = teams
        self._states = states
        self._runs = runs
        self._activity = activity
        self._history = history
        self._reports = reports

    def line(self, task: Message, result: Message | None, now: datetime) -> str:
        raise NotImplementedError("red: C-progress")
