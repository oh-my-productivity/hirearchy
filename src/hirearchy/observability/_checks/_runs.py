"""(d) Runs accounted for."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from ...agents import AgentDirectory
from ...eventlog import EventReader
from ...kernel import JsonObject, stamp_of
from ...mail import MessageFile
from ...runs import RunLogReader, RunRegistry
from .._ports import IntegrityCheck, LiveRuns
from ._base import verdict


class RunsAccounted(IntegrityCheck):
    """Every ``run.start`` has a ``run.end`` (or ``run.orphan``) or a live process, and every run log since events began has a ``run.start`` (unless the
    run never started)."""

    def __init__(self, events: EventReader, registry: RunRegistry, live: LiveRuns, agents: AgentDirectory, run_logs: RunLogReader) -> None:
        self._events, self._registry, self._live, self._agents, self._run_logs = events, registry, live, agents, run_logs

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        running = self._registry.all()
        problems: list[str] = []
        started: dict[str, JsonObject] = {}
        done: set[str] = set()
        first: datetime | None = None
        n_start = 0
        for t, ev in self._events.timed():
            k = ev.get("kind")
            if k == "scheduler.start" and (first is None or t < first):
                first = t
            elif k == "run.start" and ev.get("run"):
                started[str(ev["run"])] = ev
                n_start += 1
                if first is None or t < first:
                    first = t
            elif k in ("run.end", "run.orphan") and ev.get("run"):
                done.add(str(ev["run"]))
        if first is None:
            return verdict("d", "runs accounted for: run.start has run.end or a live process; run logs have run.start", [], "no run events yet (skipped)")
        for rid, ev in started.items():
            if rid in done:
                continue
            agent = str(ev.get("agent") or rid.rpartition("@")[0])
            rec = running.get(agent)
            if rec and Path(str(rec.get("log", ""))).stem == rid.rpartition("@")[2] and self._live.live(rec):
                continue
            problems.append(f"{rid}: run.start at {ev.get('ts')} has no run.end and no live process")
        for agent in self._agents.agents():
            for f in self._run_logs.files(agent):
                stem, path = f.stem, f.path
                begun = stamp_of(stem)
                if begun is None or begun < first or f"{agent}@{stem}" in started:
                    continue
                if self._run_logs.facts(path).get("failed_start"):
                    continue  # a run that never started has no run.start by design
                problems.append(f"{agent}@{stem}: run log without a run.start event (events began {first.isoformat(timespec='seconds')})")
        return verdict("d", "runs accounted for: run.start has run.end or a live process; run logs have run.start", problems, f"{n_start} run.start event(s) checked")
