"""The public surface of ``scheduler``: the heartbeat that wakes an agent for one fresh, short run whenever its inbox has messages.

One agent runs at most once at a time; different agents run in parallel. A run is a separate process (kiro-cli by default) whose orgmcp MCP
server is bound to the agent via ``ORG_AGENT``.

The entry point publishes no interface yet. D-sched-1 (the run lifecycle: starting a run, reaping it) works behind the ports of ``_ports``, which
this package owns because it is their only consumer; D-sched-2 (the loop, the orphans, the upkeep, the exit) adds ``SchedulerLoop`` here.
"""

from __future__ import annotations

__all__: list[str] = []
