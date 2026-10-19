"""The public surface of ``progress``: what the user who gave root's tasks reads back when they ask "status?".

One plain line per task root gave (its state, who is busy, what it cost, when anything last happened), then one line for each item in root's inbox
that waits for a decision; optionally after waiting for a change. Everything is DERIVED from the message files, the run logs and the pause flags:
nothing is stored and nothing is written, so the text can never disagree with them.

States of a task: ``working`` (someone below is running or has unread work), ``waiting on <agent>`` (the work sits with an agent that is not running;
a paused one says why), ``stalled`` (the assignee itself holds the task and nothing is happening), ``blocked: <reason>``, ``done``, ``failed``.

``wait_seconds`` turns the call into a wait: it looks at the same files again and again until a task changes state (done, failed, blocked,
stalled), something new needs the user, or the time is up. A task counts as in progress (so a wait really waits) when its state is ``working`` or
``waiting``, or when it is ``blocked``/``stalled`` but some agent in its subtree is running, or could run now.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from ..attention import HumanQueue, WaitingOnUser
from ..daemon import SchedulerStatus
from ..reflection import CaseHistory, ServiceReports

__all__ = [
    "LegacyParts",
    "ProgressReporter",
    "WAIT_MAX",
]

WAIT_MAX = 900  # longest wait_seconds honored


@runtime_checkable
class ProgressReporter(Protocol):
    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        """Status of root's tasks (``task_id``: just that one, in any state) and of what waits for the user.

        Open and blocked tasks always, finished ones while they are recent (a day), or the last finished one when nothing else is listed. Per task:
        state, who is busy, runs used against the budget given (every run of any agent in the task's subtree from its creation to its final result,
        or now, against its budget plus the later grants), the time since the team's last activity, for a finished task its artifacts and the runs
        it returned, for a service request the tag ``[service <name> v<n>]``, whether the client has rated it and the total of a rework chain.

        ``wait_seconds`` > 0 (at most ``WAIT_MAX``): first block until a listed task changes state, something new needs the user, or the time
        is up; the text then starts with a line saying which. Raises ``OrgError`` for a ``task_id`` root did not give."""
        ...

    def describe_progress(self, task_id: str | None = None, wait_seconds: int = 0) -> str:
        """``progress`` plus the scheduler line (the same text for the MCP tool and the CLI).

        Without a running scheduler nothing moves, so a wait would only burn time: it returns at once and says so. The same when every open task
        waits for the user (budget, a crashing agent, a decision): the line then says so and lists the user's options."""
        ...

    def work_in_flight(self, task_id: str | None = None) -> bool:
        """Could anything move for the listed root tasks right now: a task that is working or waiting, or blocked or stalled while an agent
        below it is running or could run. Read-only."""
        ...


@runtime_checkable
class LegacyParts(Protocol):
    """The objects the legacy functions of this package (``progress(org, task_id)`` and the private names the dashboard, the scheduler and ``observe`` still
    import) cannot build themselves, over the ports of the runtime they are handed. Not for new code; it goes with the legacy functions (step E3).

    A runtime that a test or the dashboard's lenient ``Org`` replaced a part of keeps the objects that were built over the old ports, so each call asks
    for them again over the runtime in force."""

    def human_queue(self, runtime: object) -> HumanQueue:
        """What waits for the user, read from the mailboxes ``runtime`` has now."""
        ...

    def case_history(self, runtime: object) -> CaseHistory:
        """The cases of the service requests, over the ports ``runtime`` has now."""
        ...

    def service_reports(self, runtime: object) -> ServiceReports:
        """The totals of a case, over the ports ``runtime`` has now."""
        ...

    def scheduler_status(self, runtime: object) -> SchedulerStatus:
        """The scheduler of the organization, over the ports ``runtime`` has now."""
        ...

    def waiting_on_user(self, runtime: object) -> WaitingOnUser:
        """The decision of whether everything waits for the user, over the ports ``runtime`` has now."""
        ...
