"""The runs a team made for a root task, against the runs root put into it (moved from ``progress._runs``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import ROOT, Message
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._ports import RunCounts


class LogRunCounts(RunCounts):
    """Runs: every run log of every agent in the team from the task's creation to its *final* result (``done`` or ``failed``; a ``blocked`` one is not
    final: the team may be given more budget and go on) or now. The window ends early only where root's next task to the same assignee begins, so
    overlapping tasks do not count a run twice. Run logs are files, so scheduler restarts and extra grants change nothing. Budget: the task's own plus
    every later grant (a note from root carrying budget to an agent of the team) in the same window."""

    def __init__(self, mail: MailboxReader, logs: RunLogReader) -> None:
        self._mail = mail
        self._logs = logs

    def _window(self, task: Message, result: Message | None, team: Sequence[str]) -> tuple[int, int]:
        """``(used, given)``: the runs the team made in the window of the task, and everything root put into the team in it."""
        start = task.id[:21]
        end = result.id[:21] if result is not None and result.status in ("done", "failed") else None
        sent = self._mail.sent(ROOT)
        later = [t.id[:21] for t in sent if t.type == "task" and t.to == task.to and t.id > task.id]
        if later and (end is None or later[0] < end):
            end = later[0]

        def inside(name: str) -> bool:
            return name[:21] >= start and (end is None or name[:21] <= end)

        used = sum(1 for a in team for log in self._logs.files(a) if inside(f"{log.stem}.log"))
        members = set(team)
        given = task.budget + sum(m.budget for m in sent if m.type == "note" and m.to in members and inside(m.id))
        return used, given

    def runs_text(self, task: Message, result: Message | None, team: Sequence[str]) -> str:
        used, given = self._window(task, result, team)
        text = f"runs {used} of {given}"
        if result is not None and result.budget:
            text += f" ({result.budget} returned)"
        return text

    def kept(self, task: Message, result: Message | None, team: Sequence[str]) -> int:
        if result is None or result.status not in ("done", "failed") or result.budget or not team:
            return 0
        used, given = self._window(task, result, team)
        return given - used if used < given else 0
