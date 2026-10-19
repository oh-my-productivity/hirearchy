"""The old module-level names of ``progress.py``, as thin adapters over the classes of the package.

``progress(org, task_id=None)`` is part of the permanent compatibility surface (the README documents it as the Python entry point): it keeps its
signature and its behaviour, so it stays after the legacy layer goes (E3). The other names - ``describe_progress``, ``work_in_flight`` and the private
``_human_items``, ``_can_run``, ``_state``, ``_runs``, ``_last_activity``, ``_artifacts``, ``_section`` that the dashboard, the scheduler and ``observe``
still import - go with their callers.

Every function takes the ``Org`` it is given (a feature may not import the facade, so it is duck-typed) and works over the ports that ``Org`` has *now*
(``_assembly``): the dashboard's lenient ``Org`` replaces the mailboxes, agents, budgets and flags, and tests replace parts of ``org.runtime`` under a
running call.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from ..attention import SHORT as SHORT
from ..attention import section
from ..kernel import Message
from ._activity import FsTeamActivity
from ._assembly import WaitClock, reporter_of
from ._counts import LogRunCounts
from ._lines import artifacts_of
from ._listing import RECENT as RECENT
from ._liveness import RunnableTeams
from ._ports import TaskState
from ._states import MailTaskStates
from ._wait import FINAL as FINAL
from ._wait import POLL as POLL

Org = Any  # the facade (a feature may not import it): the functions below take whatever has its methods

_artifacts = artifacts_of
_section = section


def progress(org: Org, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0,
             poll: float = POLL, sleep: Callable[[float], None] = time.sleep,
             clock: Callable[[], float] = time.monotonic) -> str:
    """Status of root's tasks (``task_id``: just that one, in any state) and of what waits for the human.

    ``wait_seconds`` > 0 (at most 900): first block until a listed task changes state (done / failed / blocked /
    stalled), something new needs the human, or the time is up; the result then starts with a line saying which.
    """
    rt = org.runtime
    return reporter_of(org, rt.progress_parts, WaitClock(rt.clock, sleep, clock), poll).progress(task_id, now, wait_seconds=wait_seconds)


def describe_progress(org: Org, task_id: str | None = None, wait_seconds: int = 0) -> str:
    """``progress`` plus the scheduler line (the same text for the MCP tool and the CLI).

    Without a running scheduler nothing moves, so a wait would only burn time: it returns at once and says so. The same
    when every open task waits for the user (budget, a crashing agent, a decision): the line then says so and lists the
    user's options.
    """
    rt = org.runtime
    return reporter_of(org, rt.progress_parts, rt.clock).describe_progress(task_id, wait_seconds)


def work_in_flight(org: Org, task_id: str | None = None) -> bool:
    """Could anything move for the listed root tasks right now? Read-only."""
    rt = org.runtime
    return reporter_of(org, rt.progress_parts, rt.clock).work_in_flight(task_id)


def _can_run(org: Org, addr: str) -> bool:
    """Is ``addr`` running, or would a scheduler start it now (unread mail that wakes it, budget left, not paused)?"""
    return RunnableTeams(org.runtime.mailbox, org.runtime.runnable_query).can_run(addr)


def _state(org: Org, task: Message, result: Message | None, team: Sequence[str]) -> TaskState:
    """(state, who is busy) of a root task."""
    rt = org.runtime
    return MailTaskStates(rt.mailbox, rt.pause_store, rt.task_query).state_of(task, result, team)


def _runs(org: Org, task: Message, result: Message | None, team: Sequence[str]) -> str:
    """Runs the team made for this task, against everything root put into the team for it."""
    return LogRunCounts(org.runtime.mailbox, org.runtime.run_log_reader).runs_text(task, result, team)


def _last_activity(org: Org, team: Sequence[str]) -> datetime | None:
    """The newest message or run in the team's mailboxes and run logs (from file names and mtimes: no parsing)."""
    return FsTeamActivity(org.runtime.paths).newest(team)


def _human_items(org: Org) -> list[tuple[str, str]]:
    """(message id, line) for each unread root message that asks for a decision (``attention.HumanQueue.items``)."""
    rt = org.runtime
    items: list[tuple[str, str]] = rt.progress_parts.human_queue(rt).items()
    return items
