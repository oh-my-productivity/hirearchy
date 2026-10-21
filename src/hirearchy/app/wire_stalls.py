"""Providers of the ``stalls`` ports (ARCHITECTURE.md 6.1), the ladder on another clock, and a resolver over a runtime.

The stall check is a phase of the scheduler's loop (D-sched-2), which times it by its cadence clock: ``ladder_on``. ``RuntimePorts`` resolves a port to the
field of a runtime that has its type, for the objects that are made over a runtime in force and not by the builder.
"""

from __future__ import annotations

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


def ladder_on(b: PortResolver, clock: Clock, views: TaskViews | None = None) -> StallLadder:
    """The ladder timed by ``clock``: the one of the runtime when that is the clock of the runtime, else one made over the same ports with this clock (the
    cadence of a scheduler, which a test may move without sleeping) and these task views (default: new ones)."""
    if clock is b.get(Clock):
        return b.get(StallLadder)
    return ladder(b, clock, views or FingerprintTaskViews(b.get(TaskQuery), b.get(MailFingerprint)))


# ------------------------------------------------------------------------------ a resolver over a runtime


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
