"""``progress``: what the user reads back when they ask "status?", optionally after waiting for a change."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio

from ..kernel import Provider
from ..progress import WAIT_MAX, ProgressReporter
from ._ports import SetupMode, ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class ProgressTools(ToolGroup):
    def __init__(self, setup: SetupMode, reporter: Provider[ProgressReporter]) -> None:
        self._setup = setup
        self._reporter = reporter

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        async def progress(task_id: str | None = None, wait_seconds: int = 0) -> str:
            """One plain status line per task you (root) gave, then what needs your decision, then the scheduler. Read-only.

        Per task: working / waiting on <agent> / stalled / blocked: <reason> / done / failed, who is busy, runs used
        of the budget given (all runs of the task's team since it was given, against its budget plus every later grant),
        time since the last activity, and for finished tasks the artifact paths and the runs returned. "Needs you"
        lists every unread note, escalation, budget request, blocked/failed result and runtime notice, with its id.
        task_id: only that task, in any state (default: open tasks and those finished in the last day).
        wait_seconds (0-900, default 0): first wait until a task finishes, fails, blocks or stalls, or something new
        needs the user, or the time is up, then answer; the answer starts with what changed. A task counts as in
        progress, so the wait really waits, while its state is working/waiting, and also while it is blocked or
        stalled but an agent below it is running or can run (unread mail that wakes it, budget left): for example the
        lead of a blocked task right after you granted it runs and called start. It answers at once only when nothing
        in the org can run, and ends early when the last thing that could run stops. Use it when the user wants to be
        told when the work is done: tell them you will wait now, call progress(wait_seconds=...) and repeat as long
        as they want (a turn cannot notify them later). Never poll with shell sleeps. Without wait_seconds it answers
        "status?".
        """
            if self._setup.active():
                return self._setup.state()
            reporter = self._reporter()
            wait = max(0, min(int(wait_seconds or 0), WAIT_MAX))
            return await anyio.to_thread.run_sync(reporter.describe_progress, task_id, wait)
