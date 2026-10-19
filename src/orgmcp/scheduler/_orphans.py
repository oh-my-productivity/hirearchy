"""The runs of a dead scheduler: killed if they are verifiably ours, redelivered if they are gone, kept (and the agent blocked) if in doubt."""

from __future__ import annotations

from collections.abc import Mapping

from ..kernel import EventSink
from ..processes import OrphanJudge, ProcessSignaller
from ..runs import RunLogWriter, RunRegistry
from ._ports import Console, OrphanSettler, RunNotes
from ._run import RunTable


class LogRunNotes(RunNotes):
    def __init__(self, writer: RunLogWriter) -> None:
        raise NotImplementedError("red: D-sched-2")

    def note(self, rec: Mapping[str, object], text: str) -> None:
        raise NotImplementedError("red: D-sched-2")


class LedgerOrphanSettler(OrphanSettler):
    def __init__(
        self, registry: RunRegistry, judge: OrphanJudge, signaller: ProcessSignaller, notes: RunNotes, events: EventSink, console: Console
    ) -> None:
        raise NotImplementedError("red: D-sched-2")

    def settle(self, runs: RunTable, blocked: set[str]) -> None:
        raise NotImplementedError("red: D-sched-2")
