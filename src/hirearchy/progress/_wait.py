"""Progress with an optional wait (moved from ``progress.progress``, ``_changes`` and the constants)."""

from __future__ import annotations

from datetime import datetime

from ..kernel import Clock, fmt_duration
from ._ports import ProgressText, ProgressView, Snapshot, Snapshots
from ._snapshot import moving
from .api import WAIT_MAX

POLL = 2.0  # seconds between two looks at the files while waiting
FINAL = ("done", "failed", "blocked", "stalled")  # the states a wait returns for


def changes(before: Snapshot, after: Snapshot, suspect: set[str]) -> tuple[list[str], set[str]]:
    """What differs between two snapshots, as short phrases, and the tasks to confirm as stalled on the next look."""
    out: list[str] = []
    seen: set[str] = set()
    for tid, mark in after.marks.items():
        old = before.marks.get(tid)
        if old is None or mark.kind == old.kind or mark.kind not in FINAL:
            continue
        if mark.kind == "stalled" and tid not in suspect:
            seen.add(tid)
            continue
        out.append(f'"{mark.title}": {old.kind} -> {mark.state}')
    out += [f"new item for you: {line}" for mid, line in after.needs.items() if mid not in before.needs]
    return out, seen


class PollingProgress(ProgressView):
    """``wait_seconds`` > 0 (at most ``WAIT_MAX``): first look at the files every ``poll`` seconds (read-only: no locks, nothing written) until a listed
    task changes state (done / failed / blocked / stalled), something new needs the user, or the time is up; the result then starts with a line saying which."""

    def __init__(self, text: ProgressText, snapshots: Snapshots, clock: Clock, poll: float = POLL) -> None:
        self._text = text
        self._snapshots = snapshots
        self._clock = clock
        self._poll = poll

    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        wait = max(0, min(int(wait_seconds or 0), WAIT_MAX))
        if wait <= 0:
            return self._text.render(task_id, now)
        before = self._snapshots.snapshot(task_id)
        if not moving(before):
            return "Nothing to wait for: no listed task is being worked on right now.\n" + self._text.render(task_id, now)
        start = self._clock.monotonic()
        suspect: set[str] = set()  # tasks seen stalled once: confirmed on the next look, so a hand-over is not a stall
        idle = 0  # consecutive looks at which nothing in the org could run any more
        while True:
            left = wait - (self._clock.monotonic() - start)
            self._clock.sleep(max(0.0, min(self._poll, left)))
            after = self._snapshots.snapshot(task_id)
            found, suspect = changes(before, after, suspect)
            waited = fmt_duration(max(0.0, self._clock.monotonic() - start))
            if found:
                return f"Changed after waiting {waited}: " + "; ".join(found) + "\n" + self._text.render(task_id, now)
            idle = 0 if moving(after) else idle + 1
            if idle >= 2:  # twice in a row, so the gap between one run ending and the next starting is not mistaken for it
                return (f"Stopped after waiting {waited}: nothing in the org can run any more and no task finished. "
                        "It needs a decision, budget or a restart (see below).\n" + self._text.render(task_id, now))
            if self._clock.monotonic() - start >= wait:
                return (f"Waited {waited}: no task finished, got blocked or stalled, and nothing new needs you. "
                        "Call progress(wait_seconds=...) again to keep waiting.\n" + self._text.render(task_id, now))
