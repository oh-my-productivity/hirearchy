"""The line of a root task (moved from ``progress._task_line``, ``_rated`` and ``_artifacts``)."""

from __future__ import annotations

from datetime import datetime

from ..attention import section
from ..kernel import ROOT, Message, client_questions, fmt_duration
from ..mail import MailboxReader
from ..reflection import Case, CaseHistory, ServiceReports, rated
from ._ports import RunCounts, TaskLines, TaskStates, TaskTeams, TeamActivity


def artifacts_of(result: Message) -> list[str]:
    """Paths listed under ``## Artifacts`` (the runtime's word-count notes after the path are dropped)."""
    return [line.lstrip("-* ").split(" (", 1)[0] for line in section(result.body, "artifacts")]


class CaseTaskLines(TaskLines):
    def __init__(
        self, teams: TaskTeams, states: TaskStates, runs: RunCounts, activity: TeamActivity, history: CaseHistory, reports: ServiceReports,
        mail: MailboxReader,
    ) -> None:
        self._teams = teams
        self._states = states
        self._runs = runs
        self._activity = activity
        self._history = history
        self._reports = reports
        self._mail = mail

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
        case = self._history.case_of(task) if task.service else None
        if result is not None and result.status in ("done", "failed"):
            arts = artifacts_of(result)
            parts.append("artifacts: " + ", ".join(arts) if arts else "no artifacts")
            asked = self._questions_to_ask(task, result, case)
            if asked:
                parts.append(f"{asked} question{'' if asked == 1 else 's'} for the client: ask the user before you copy or deliver")
        if task.service:
            if result is not None and result.status in ("done", "failed") and not rated(case, task):
                parts.append("no feedback yet")
            if case is not None and case.reworks:  # a rework chain: the line above is one request, this is the whole case
                parts.append(self._reports.case_total(task).rstrip("."))
        return ". ".join(parts) + f". (task {task.id})"

    def _questions_to_ask(self, task: Message, result: Message, case: Case | None) -> int:
        """The client questions of a done result that nobody has answered yet; 0 when there are none or they are settled.

        The user's own rework of the task answers them, so does the client's verdict on the delivery. The assistant's own (relayed) rework does not."""
        if result.status != "done":
            return 0
        asked = len(client_questions(result.body))
        if asked == 0 or (task.service and rated(case, task)):
            return 0
        reworked = any(t.type == "task" and t.revises == task.id and t.source == "human" for t in self._mail.sent(ROOT))
        return 0 if reworked else asked
