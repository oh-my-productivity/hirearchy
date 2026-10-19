"""Providers of the ``stalls`` ports (ARCHITECTURE.md 6.1), and the ladder of the legacy scheduler.

``RuntimeStalls`` and ``CallableClock`` serve ``scheduler.Scheduler`` until D-sched-1 converts it: it is given its clock as a function and its org
as an object whose ``runtime`` tests replace, and it keeps the memo of the task views for as long as it lives. Both are deleted then.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar, cast

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..eligibility import PauseStore
from ..kernel import Clock, EventSink, LedgerStore, Message, OrgLayout
from ..mail import MailboxReader, MailFingerprint, TaskQuery
from ..runs import RunLogReader
from ..settings import OrgSettings
from ..stalls import NudgeLedger, StallLadder
from ..stalls._ladder import EscalationStallLadder
from ..stalls._nudges import LedgerNudgeLedger
from ..stalls._ports import FsCreationTimes, FsLedgerShape, TaskViews
from ..stalls._views import FingerprintTaskViews
from ..templates import Notices
from ._builder import Builder
from ._lazy import PortResolver, ports_of
from .runtime import OrgRuntime


def nudge_ledger(b: PortResolver) -> LedgerNudgeLedger:
    """The ledger over the ledgers, the layout and the agents of the runtime (it is both the reader and the writer of ``.runtime/nudges.json``)."""
    return LedgerNudgeLedger(b.get(LedgerStore), FsLedgerShape(b.get(OrgLayout)), b.get(AgentDirectory))


def ladder(b: PortResolver, clock: Clock, views: TaskViews) -> EscalationStallLadder:
    """The ladder over the ports ``b`` builds, with this clock and these task views."""
    nudges = nudge_ledger(b)
    return EscalationStallLadder(
        clock, b.get(OrgSettings), b.get(AgentDirectory), views, b.get(MailboxReader), b.get(PauseStore), b.get(RunLogReader), FsCreationTimes(),
        nudges, nudges, b.get(MessageDelivery), b.get(Notices), b.get(EventSink),
    )


def register(b: Builder) -> None:
    b.provide(NudgeLedger, nudge_ledger)
    b.provide(StallLadder, lambda b: ladder(b, b.get(Clock), FingerprintTaskViews(b.get(TaskQuery), b.get(MailFingerprint))))


# ------------------------------------------------------------------------------ the legacy scheduler's ladder


class CallableClock(Clock):
    """A ``Clock`` whose time is a function (``Scheduler(clock=...)``): ``now`` and ``time`` follow it, waits are the system's."""

    def __init__(self, seconds: Callable[[], float]) -> None:
        self._seconds = seconds

    def now(self) -> datetime:
        return datetime.fromtimestamp(self._seconds(), timezone.utc)

    def time(self) -> float:
        return self._seconds()

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


T = TypeVar("T")


class RuntimePorts(PortResolver):
    """A resolver over the ports of an ``OrgRuntime`` (each port is the field of the runtime that has its type)."""

    def __init__(self, runtime: OrgRuntime) -> None:
        self._runtime = runtime
        self._fields = {port: name for name, port in ports_of(OrgRuntime).items()}

    @property
    def root(self) -> Path:
        return self._runtime.root

    def get(self, port: type[T]) -> T:
        return cast(T, getattr(self._runtime, self._fields[port]))


class RuntimeStalls:
    """The ladder of a legacy scheduler, over the ports of the runtime in force at each call.

    Tests replace ``org.runtime`` under a running scheduler, so the ports are not fixed when the scheduler is made; the memo of the task views, which the
    scheduler always kept for itself, is carried over to the ladder of the new runtime."""

    def __init__(self, runtime: Callable[[], OrgRuntime], clock: Callable[[], float]) -> None:
        raise NotImplementedError("red: C-stalls")

    def check(self) -> list[str]:
        raise NotImplementedError("red: C-stalls")

    def task_view(self, addr: str, view: str) -> list[Message]:
        """``open_tasks`` or ``outstanding`` of an agent, as the ladder sees them (``Scheduler._task_view``)."""
        raise NotImplementedError("red: C-stalls")
