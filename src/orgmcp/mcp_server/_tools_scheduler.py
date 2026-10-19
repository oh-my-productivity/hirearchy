"""``start`` and ``stop``: the scheduler of the organization, from the human's seat."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..attention import OpenWork, WaitingOnUser
from ..daemon import SchedulerControl, SchedulerStatus
from ..kernel import OrgLayout, Provider
from ._ports import ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class SchedulerTools(ToolGroup):
    def __init__(
        self, control: Provider[SchedulerControl], status: Provider[SchedulerStatus], waiting: Provider[WaitingOnUser],
        work: Provider[OpenWork], layout: Provider[OrgLayout],
    ) -> None:
        self._control = control
        self._status = status
        self._waiting = waiting
        self._work = work
        self._layout = layout

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def start(max_runs: int | None = None, until_done: bool = True) -> str:
            """Start the scheduler for this organization in the background; it wakes agents that have mail.

        max_runs: stop starting agent runs after this many (safety cap; default: no cap). until_done (default True):
        the scheduler exits by itself when you have no open task and nothing is running or can run, so you need not
        stop it (status and progress then say "scheduler: stopped (finished: no open tasks)"); start it again after
        giving the org more work. It also exits by itself, after a few minutes (`until_done_grace_seconds`), when every
        open task is waiting for YOU (an agent is out of budget or keeps failing, or a task is stalled): status and
        progress then say "stopped (waiting on you: ...)" with your options. start() refuses while that is the case:
        grant runs first (send(to=<agent>, body=<why>, budget=N)). False keeps it running until stop(). Refused if one
        is already running. Output goes to .runtime/scheduler.log. Returns the scheduler's pid.
        """
            status = self._status()
            if until_done and status.state().state == "stopped" and self._work().nothing_to_do():
                return ("not started: there is nothing to run (you have no open task and no agent has work). Give the "
                        "organization work first (apply_org or delegate), then call start(); until_done=False would "
                        "keep an idle scheduler running instead")
            if status.state().state == "stopped" and (waiting := self._waiting().analyze()):
                return (f"not started: nothing can progress without you, so a scheduler would only sit idle. {waiting.text}. "
                        f"{waiting.options}")
            pid = self._control().start(max_runs, until_done)
            cap = f", at most {max_runs} run(s)" if max_runs is not None else ""
            end = "; it exits by itself when the work is done" if until_done else "; it runs until stop()"
            return f"scheduler started (pid {pid}{cap}{end}); log: {self._layout().runtime_dir() / 'scheduler.log'}"

        @mcp.tool()
        def stop() -> str:
            """Stop this organization's scheduler (SIGTERM, then wait briefly). Runs in flight are interrupted and
        redelivered on the next start. Only signals a process verified to be this organization's scheduler."""
            return self._control().stop()
