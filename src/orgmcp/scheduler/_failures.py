"""Failed runs: the count in a row, and the pause with its notices at ``max_failures``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..delivery import MessageDelivery
from ..eligibility import FailureCounter, PauseStore
from ..kernel import ROOT, EventSink, OrgLayout, parent, single
from ..settings import OrgSettings
from ..templates import Notices
from ._ports import Console, FailureEscalation, RunFailures


class PausingEscalation(FailureEscalation):
    """At ``max_failures`` failed runs in a row the agent is paused; its parent is told, and the human too when the parent is not the human."""

    def __init__(self, pauses: PauseStore, delivery: MessageDelivery, notices: Notices, settings: OrgSettings, layout: OrgLayout) -> None:
        self._pauses, self._delivery, self._notices, self._settings, self._layout = pauses, delivery, notices, settings, layout

    def escalate(self, addr: str, count: int, log: Path, traces: Sequence[str]) -> None:
        if count >= self._settings.number("max_failures", int):
            self._pauses.pause(addr, "failures", by="runtime")
            rel = str(log.relative_to(self._layout.root))
            manager = parent(addr) or ROOT
            trace = single(traces)
            self._delivery.notify(manager, f"{addr} keeps failing", self._notices.failures(addr, count, rel, to_human=manager == ROOT), trace=trace)
            if manager != ROOT:  # a human has to look at crashes
                self._delivery.notify(ROOT, f"{addr} keeps failing", self._notices.failures(addr, count, rel), trace=trace)


class CountingFailures(RunFailures):
    def __init__(self, counter: FailureCounter, escalation: FailureEscalation, events: EventSink, console: Console) -> None:
        self._counter, self._escalation, self._events, self._console = counter, escalation, events, console

    def failed(self, addr: str, log: Path, traces: Sequence[str]) -> None:
        n = self._counter.record(addr)
        self._events.emit("agent.failure", agent=addr, count=n, trace=single(traces))
        self._console.say(f"{addr}: run failed ({n} in a row), log: {log}")
        self._escalation.escalate(addr, n, log, traces)

    def cleared(self, addr: str) -> None:
        self._counter.clear(addr)
