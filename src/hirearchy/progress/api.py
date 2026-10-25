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

from ..kernel import JsonObject

__all__ = [
    "ProgressReporter",
    "QualityReport",
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
        A done or blocked result whose ``Questions for the client:`` block holds a question that names a criterion id (``C<k>``) is flagged "ask the
        user before you copy or deliver", and its path withheld, until the user's own rework or the client's verdict answers it (a rework root
        relayed does not); the block's other items are listed as notes for the client, never withheld.

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
class QualityReport(Protocol):
    def quality_text(self, service: str | None = None) -> str:
        """How the work root asked for has gone, from the files (0b 9): per service, and for root's one-off tasks, the cases, the user's verdicts on first
        deliveries in their words, escapes with the verifier that signed them off and the cause a rule typed, deliveries without a verdict and files not
        as delivered, the user's runs against the runs the user approved, two alarms (repeat, cost), the timeline of bar changes, and the blocked tasks
        moved past without a verdict. ``service`` limits it to one service (empty or ``None``: everything). Read-only. ``OrgError`` for a ``service`` no agent
        offers (it lists the names) or one longer than 80 characters; ``OrgError``/``OSError`` when the agents cannot be listed. A file that does not parse
        degrades the part it feeds and is never raised."""
        ...

    def quality_data(self, service: str | None = None) -> JsonObject:
        """The same data as ``quality_text`` as plain JSON values (schema 1, 0b 9.4): every key always present, no text limits, the playbook versions'
        changed lines included. Same errors."""
        ...
