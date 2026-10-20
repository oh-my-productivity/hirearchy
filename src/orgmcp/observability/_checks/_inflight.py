"""(c) Nothing inflight without a live run."""

from __future__ import annotations

from collections.abc import Sequence

from ...agents import AgentDirectory
from ...daemon import SchedulerStatus
from ...kernel import JsonObject, fmt_dur
from ...mail import MessageFile
from ...runs import RunRegistry
from .._ports import IntegrityCheck, LiveRuns, MailboxFiles
from ._base import INFLIGHT_GRACE, verdict


class InflightAccounted(IntegrityCheck):
    """An agent whose inflight box holds messages has a run going (its process is recorded alive), or the scheduler has only just begun the run."""

    def __init__(self, agents: AgentDirectory, files: MailboxFiles, registry: RunRegistry, live: LiveRuns, scheduler: SchedulerStatus) -> None:
        self._agents, self._files, self._registry, self._live, self._scheduler = agents, files, registry, live, scheduler

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        st = self._scheduler.state()
        running = self._registry.all()
        problems = []
        for a in self._agents.agents():
            names = self._files.names(a, "inflight")
            if not names:
                continue
            if self._live.live(running.get(a)):
                continue
            age = max((now - m for n in names if (m := self._files.mtime(a, "inflight", n)) is not None), default=0.0)
            if st.state == "running" and age <= INFLIGHT_GRACE:
                continue  # the scheduler has just begun this run
            problems.append(f"{a}: {len(names)} message(s) inflight for {fmt_dur(age * 1000)} but no live run"
                            + (" (no scheduler is running)" if st.state != "running" else " (the scheduler has no live process for it)"))
        return verdict("c", "nothing inflight without a live run", problems, "no agent has an unfinished batch without a run")
