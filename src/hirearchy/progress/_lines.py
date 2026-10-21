"""The line of a root task (moved from ``progress._task_line``, ``_rated`` and ``_artifacts``)."""

from __future__ import annotations

from datetime import datetime

from ..attention import section
from ..kernel import Message, fmt_duration
from ..reflection import Case, CaseHistory, ServiceReports
from ._ports import RunCounts, TaskLines, TaskStates, TaskTeams, TeamActivity


def artifacts_of(result: Message) -> list[str]:
    """Paths listed under ``## Artifacts`` (the runtime's word-count notes after the path are dropped)."""
    return [line.lstrip("-* ").split(" (", 1)[0] for line in section(result.body, "artifacts")]


def rated(case: Case | None, task: Message) -> bool:
    """Has the client given feedback on this delivery (or on a later rework of it)? An earlier verdict does not count."""
    if case is None:
        return False
    step = next((i for i, t in enumerate(case.tasks) if t.id == task.id), 0)
    return any(v.step >= step for v in case.verdicts)


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
        team = self._teams.team_of(task)
        state, who = self._states.state_of(task, result, team)
        tag = f" [service {task.service} v{task.playbook or 0}]" if task.service else ""
        parts = [f'"{task.title}"{tag}: {state}']
        if who:
            parts.append(who)
        parts.append(self._runs.runs_text(task, result, team))
        if self._runs.kept(task, result, team):
            parts.append(f"0 returned (kept by {task.to})")
        last = self._activity.newest(team)
        if last is not None:
            parts.append(f"last activity {fmt_duration(max(0.0, (now - last).total_seconds()))} ago")
        if result is not None and result.status in ("done", "failed"):
            arts = artifacts_of(result)
            parts.append("artifacts: " + ", ".join(arts) if arts else "no artifacts")
        if task.service:
            case = self._history.case_of(task)
            if result is not None and result.status in ("done", "failed") and not rated(case, task):
                parts.append("no feedback yet")
            if case is not None and case.reworks:  # a rework chain: the line above is one request, this is the whole case
                parts.append(self._reports.case_total(task).rstrip("."))
        return ". ".join(parts) + f". (task {task.id})"
