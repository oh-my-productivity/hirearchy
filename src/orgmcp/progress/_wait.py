"""Progress with an optional wait (moved from ``progress.progress``, ``_changes`` and the constants)."""

from __future__ import annotations

from datetime import datetime

from ..kernel import Clock
from ._ports import ProgressText, ProgressView, Snapshot, Snapshots

POLL = 2.0  # seconds between two looks at the files while waiting
FINAL = ("done", "failed", "blocked", "stalled")  # the states a wait returns for


def changes(before: Snapshot, after: Snapshot, suspect: set[str]) -> tuple[list[str], set[str]]:
    """What differs between two snapshots, as short phrases, and the tasks to confirm as stalled on the next look."""
    raise NotImplementedError("red: C-progress")


class PollingProgress(ProgressView):
    def __init__(self, text: ProgressText, snapshots: Snapshots, clock: Clock, poll: float = POLL) -> None:
        self._text = text
        self._snapshots = snapshots
        self._clock = clock
        self._poll = poll

    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        raise NotImplementedError("red: C-progress")
