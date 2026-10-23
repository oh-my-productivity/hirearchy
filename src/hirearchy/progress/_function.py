"""``progress(org, task_id=None)``: the permanent Python entry point of the package (the README documents it).

It is a thin function over the ports of the runtime of the ``org`` it is given (a feature may not import the facade, so ``org`` is duck-typed): the
text is the one the ``ProgressReporter`` of that runtime gives, except that the waits (``sleep``, ``clock``, ``poll``) are the caller's.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ..kernel import Clock
from ._activity import FsTeamActivity
from ._counts import LogRunCounts
from ._lines import CaseTaskLines
from ._listing import MailRootTasks
from ._liveness import RunnableTeams
from ._render import RootTaskReport
from ._snapshot import TeamSnapshots
from ._states import MailTaskStates
from ._teams import AgentTaskTeams
from ._wait import POLL, PollingProgress

Org = Any  # the facade (a feature may not import it): the function below takes whatever has its runtime


class WaitClock(Clock):
    """The time of day of ``inner``, and the waits of a caller who gives them as functions (``progress(org, sleep=..., clock=...)``)."""

    def __init__(self, inner: Clock, sleep: Callable[[float], None], monotonic: Callable[[], float]) -> None:
        self._inner = inner
        self._sleep = sleep
        self._monotonic = monotonic

    def now(self) -> datetime:
        return self._inner.now()

    def time(self) -> float:
        return self._inner.time()

    def monotonic(self) -> float:
        return self._monotonic()

    def sleep(self, seconds: float) -> None:
        self._sleep(seconds)


def progress(org: Org, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0,
             poll: float = POLL, sleep: Callable[[float], None] = time.sleep,
             clock: Callable[[], float] = time.monotonic) -> str:
    """Status of root's tasks (``task_id``: just that one, in any state) and of what waits for the human.

    ``wait_seconds`` > 0 (at most 900): first block until a listed task changes state (done / failed / blocked /
    stalled), something new needs the human, or the time is up; the result then starts with a line saying which.
    """
    rt = org.runtime
    time_of = WaitClock(rt.clock, sleep, clock)
    roots, teams, states = MailRootTasks(rt.mailbox), AgentTaskTeams(rt.agents), MailTaskStates(rt.mailbox, rt.pause_store, rt.task_query)
    lines = CaseTaskLines(
        teams, states, LogRunCounts(rt.mailbox, rt.run_log_reader), FsTeamActivity(rt.paths), rt.case_history, rt.service_reports,
        rt.mailbox,
    )
    snapshots = TeamSnapshots(roots, teams, states, RunnableTeams(rt.mailbox, rt.runnable_query), rt.human_queue, time_of)
    view = PollingProgress(RootTaskReport(roots, lines, rt.human_queue, time_of, rt.deliverable_checks), snapshots, time_of, poll)
    return view.progress(task_id, now, wait_seconds=wait_seconds)
