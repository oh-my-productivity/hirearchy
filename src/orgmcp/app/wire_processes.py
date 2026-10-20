"""Providers of the ports of ``processes`` (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..kernel import Clock, Environment
from ..processes import OrphanJudge, ProcessInspector, ProcessSignaller, ProcessSpawner
from ..processes._inspect import PsProcessInspector
from ..processes._judge import PsOrphanJudge
from ..processes._signal import OsProcessSignaller
from ..processes._spawn import PopenProcessSpawner
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(ProcessSpawner, lambda b: PopenProcessSpawner())
    b.provide(ProcessInspector, lambda b: PsProcessInspector(b.get(Environment)))
    b.provide(ProcessSignaller, lambda b: OsProcessSignaller(b.get(ProcessInspector), b.get(Clock)))
    b.provide(OrphanJudge, lambda b: PsOrphanJudge(b.get(ProcessInspector)))
