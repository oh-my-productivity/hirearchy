"""The runs of a dead scheduler: killed if they are verifiably ours, redelivered if they are gone, kept (and the agent blocked) if in doubt."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from ..kernel import EventSink
from ..processes import OrphanJudge, ProcessSignaller
from ..runs import RunLogWriter, RunRegistry, run_id_of
from ._ports import Console, OrphanSettler, RunNotes
from ._run import RunTable


class LogRunNotes(RunNotes):
    """The notes go to the run log the record names."""

    def __init__(self, writer: RunLogWriter) -> None:
        self._writer = writer

    def note(self, rec: Mapping[str, object], text: str) -> None:
        try:
            rel = str(rec["log"])
        except KeyError:
            return
        self._writer.append_note(rel, text)


class LedgerOrphanSettler(OrphanSettler):
    """Kill runs a dead scheduler left behind, and note those that survive.

    Called when a scheduler starts (any record then belongs to a dead one: the claim has just checked that no other scheduler lives) and every tick while
    some orphan could not be dealt with. A recorded process is killed only if the judge says it is ours; one that is alive but cannot be verified or killed
    keeps its agent from starting a new run until it is gone.
    """

    def __init__(
        self, registry: RunRegistry, judge: OrphanJudge, signaller: ProcessSignaller, notes: RunNotes, events: EventSink, console: Console
    ) -> None:
        self._registry, self._judge, self._signaller, self._notes, self._events, self._console = registry, judge, signaller, notes, events, console

    def settle(self, runs: RunTable, blocked: set[str]) -> None:
        records = self._registry.all()
        keep = {}
        for addr, rec in records.items():
            if addr in runs or (blocked and addr not in blocked):
                keep[addr] = rec
                continue
            verdict = self._judge.judge(rec)
            pgid = rec.get("pgid")
            rid = run_id_of(addr, cast("str", rec["log"])) if rec.get("log") else None
            if verdict == "ours":
                if self._signaller.kill_group(cast(int, pgid)):
                    self._console.say(f"{addr}: killed the orphaned run of a dead scheduler (process group {pgid})")
                    self._notes.note(rec, "killed: orphaned run of a scheduler that died")
                    self._events.emit("run.orphan", agent=addr, run=rid, action="killed",
                                      detail=f"process group {pgid} of a dead scheduler killed; its batch is redelivered")
                    verdict = "gone"
                else:
                    verdict = "doubt"
            elif verdict == "gone":
                self._events.emit("run.orphan", agent=addr, run=rid, action="redelivered",
                                  detail="the process of a dead scheduler's run is gone; its batch is redelivered")
            if verdict == "foreign":
                self._console.say(f"{addr}: recorded process {pgid} is not the run we started; left alone")
                self._events.emit("run.orphan", agent=addr, run=rid, action="redelivered",
                                  detail=f"pid {pgid} now belongs to another process (left alone); the run's batch is redelivered")
            elif verdict == "doubt":
                if addr not in blocked:
                    self._events.emit("run.orphan", agent=addr, run=rid, action="kept",
                                      detail=f"process group {pgid} may be alive and cannot be verified or killed; no new run until it is gone")
                keep[addr] = rec
                if addr not in blocked:
                    self._console.say(f"{addr}: an earlier run (process group {pgid}) may still be alive and cannot be "
                                      "verified or killed; no new run until it is gone")
                blocked.add(addr)
                continue
            blocked.discard(addr)
        blocked &= set(keep)
        if keep != records:
            self._registry.replace(keep)
