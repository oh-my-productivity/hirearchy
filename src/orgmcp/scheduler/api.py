"""The public surface of ``scheduler``: the heartbeat that wakes an agent for one fresh, short run whenever its inbox has messages.

One agent runs at most once at a time; different agents run in parallel. A run is a separate process (kiro-cli by default) whose orgmcp MCP
server is bound to the agent via ``ORG_AGENT``.

The entry point publishes one interface, ``SchedulerLoop``: the loop itself, which a caller (the ``orgmcp run`` command) starts and stops. The
roles the loop is made of - the run lifecycle (starting and reaping runs), the orphans of a dead scheduler, the upkeep, the exit policy, the guard
of the best-effort phases - are ports of ``_ports``, which this package owns because it is their only consumer.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["SchedulerLoop"]


@runtime_checkable
class SchedulerLoop(Protocol):
    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        """Acquire, loop, release. ``until_idle``: exit once nothing runs and nothing could start; ``until_done``: exit once root has no open task and
        nothing is running or runnable, or once nothing can progress without the user (for ``until_done_grace_seconds``); ``max_runs``: stop starting
        runs after this many. SIGTERM ends the loop cleanly; the runs in flight are interrupted and their batches redelivered later."""
        ...

    def run_once(self, max_runs: int | None = None) -> None:
        """``orgmcp run --once``: acquire, one pass, wait for the runs it started, release."""
        ...

    def tick(self, max_runs: int | None = None) -> bool:
        """One pass: reap finished runs, start new ones, detect stalls, review health, keep up the event log. True if work remains."""
        ...

    def finished(self, max_runs: int | None = None) -> bool:
        """Nothing left for an until-done scheduler: root has no open task, no run is in flight, no agent could start."""
        ...
