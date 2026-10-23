"""The report: the lines of the listed tasks, then what needs the user (moved from ``progress._render``)."""

from __future__ import annotations

from datetime import datetime

from ..attention import HumanQueue
from ..kernel import ROOT, Clock, Message, OrgError, aware
from ..reflection import DeliverableChecks, deliverables_note
from ._listing import listed
from ._ports import ProgressText, RootTasks, TaskLines


class RootTaskReport(ProgressText):
    def __init__(self, roots: RootTasks, lines: TaskLines, queue: HumanQueue, clock: Clock, deliverables: DeliverableChecks) -> None:
        self._roots = roots
        self._lines = lines
        self._queue = queue
        self._clock = clock
        self._deliverables = deliverables

    def render(self, task_id: str | None, now: datetime | None) -> str:
        now = aware(now) or self._clock.now()
        tasks = self._roots.tasks()
        results = self._roots.latest_results()
        if task_id:
            task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                known = ", ".join(t.id for t in tasks) or "none"
                raise OrgError(f"no task {task_id} given by root. Tasks: {known}")
            lines = [self._lines.line(task, results.get(task.id), now)]
            if task.service:  # a goal given with `delegate` has no service, so no folder
                lines += self._deliverables_note(task.service)
        else:
            lines = [
                self._lines.line(t, results.get(t.id), now) for t in tasks if listed(results.get(t.id), now)
            ] or ["No open tasks." + self._last_finished(tasks, results, now)]
            lines += self._deliverables_note(None)
        lines += self._queue.lines()
        return "\n".join(lines)

    def _deliverables_note(self, service: str | None) -> list[str]:
        """The files of the deliverable folders (of one service, or of every service root requests) that are not what the team delivered as checked,
        as lines for root; none when there is nothing to say or when the folders cannot be looked at (a catalog or a mailbox that cannot be read)."""
        try:
            return deliverables_note(self._deliverables.findings(ROOT, service)).splitlines()
        except (OrgError, OSError):
            return []

    def _last_finished(self, tasks: list[Message], results: dict[str, Message], now: datetime) -> str:
        done = [t for t in tasks if (r := results.get(t.id)) and r.status != "blocked"]
        return "\n" + self._lines.line(done[-1], results[done[-1].id], now) if done else ""
