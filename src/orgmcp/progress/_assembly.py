"""The reporter over the ports an ``Org`` has *now*: what the legacy functions need (not a port of the package).

The legacy functions are handed an ``Org`` (duck-typed: a feature may not import the facade). They build the classes over the ports that ``Org`` has at the
moment of the call, not over the ones its runtime was first opened with: the dashboard's lenient ``Org`` replaces the agents, the mailboxes, the budgets
and the pause flags with tolerant, cached variants, and tests replace parts of ``org.runtime`` under a running call. What the package cannot build itself
(the queue of what needs the user, the history of the cases, the scheduler status, the decision of the user) it asks ``LegacyParts`` for.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from ..kernel import Clock
from ._activity import FsTeamActivity
from ._lines import CaseTaskLines
from ._liveness import RunnableTeams
from ._listing import MailRootTasks
from ._render import RootTaskReport
from ._reporter import DerivedProgressReporter
from ._counts import LogRunCounts
from ._snapshot import TeamSnapshots
from ._states import MailTaskStates
from ._teams import AgentTaskTeams
from ._wait import POLL, PollingProgress
from .api import LegacyParts


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


def reporter_of(org: Any, parts: LegacyParts, clock: Clock, poll: float = POLL) -> DerivedProgressReporter:
    rt = org.runtime
    roots, teams, states = MailRootTasks(rt.mailbox), AgentTaskTeams(rt.agents), MailTaskStates(rt.mailbox, rt.pause_store, rt.task_query)
    queue = parts.human_queue(rt)
    lines = CaseTaskLines(
        teams, states, LogRunCounts(rt.mailbox, rt.run_log_reader), FsTeamActivity(rt.paths), parts.case_history(rt), parts.service_reports(rt),
    )
    snapshots = TeamSnapshots(roots, teams, states, RunnableTeams(rt.mailbox, rt.runnable_query), queue, clock)
    view = PollingProgress(RootTaskReport(roots, lines, queue, clock), snapshots, clock, poll)
    return DerivedProgressReporter(view, snapshots, parts.scheduler_status(rt), parts.waiting_on_user(rt), rt.task_query)
