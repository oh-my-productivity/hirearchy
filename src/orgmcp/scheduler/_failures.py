"""Failed runs: the count in a row, and the pause with its notices at ``max_failures``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..delivery import MessageDelivery
from ..eligibility import FailureCounter, PauseStore
from ..kernel import EventSink, OrgLayout
from ..settings import OrgSettings
from ..templates import Notices
from ._ports import Console, FailureEscalation, RunFailures


class PausingEscalation(FailureEscalation):
    def __init__(self, pauses: PauseStore, delivery: MessageDelivery, notices: Notices, settings: OrgSettings, layout: OrgLayout) -> None:
        raise NotImplementedError("red: D-sched-1")

    def escalate(self, addr: str, count: int, log: Path, traces: Sequence[str]) -> None:
        raise NotImplementedError("red: D-sched-1")


class CountingFailures(RunFailures):
    def __init__(self, counter: FailureCounter, escalation: FailureEscalation, events: EventSink, console: Console) -> None:
        raise NotImplementedError("red: D-sched-1")

    def failed(self, addr: str, log: Path, traces: Sequence[str]) -> None:
        raise NotImplementedError("red: D-sched-1")

    def cleared(self, addr: str) -> None:
        raise NotImplementedError("red: D-sched-1")
