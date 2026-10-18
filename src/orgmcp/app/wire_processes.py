"""Providers of the ports of ``processes`` (ARCHITECTURE.md 6.1), and the constructors the legacy modules still need.

The legacy ``scheduler.py`` helpers (``_ps``, ``judge_orphan``, ``kill_group``, ...) have no runtime to take the ports from, so they ask
this module for the system ones; they go away with ``scheduler.py`` (D-sched-1).
"""

from __future__ import annotations

import subprocess

from ..kernel import Clock, Environment
from ..kernel._system import OsEnvironment, SystemClock
from ..processes import OrphanJudge, ProcessHandle, ProcessInspector, ProcessSignaller, ProcessSpawner
from ..processes._inspect import PsProcessInspector
from ..processes._judge import PsOrphanJudge
from ..processes._signal import OsProcessSignaller
from ..processes._spawn import PopenHandle, PopenProcessSpawner
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(ProcessSpawner, lambda b: PopenProcessSpawner())
    b.provide(ProcessInspector, lambda b: PsProcessInspector(b.get(Environment)))
    b.provide(ProcessSignaller, lambda b: OsProcessSignaller(b.get(ProcessInspector), b.get(Clock)))
    b.provide(OrphanJudge, lambda b: PsOrphanJudge(b.get(ProcessInspector)))


# ------------------------------------------------------------------------------ for the legacy modules (no runtime at hand)


def adopt(proc: subprocess.Popen[str]) -> ProcessHandle:
    """A handle on a process that a legacy module started with ``subprocess.Popen``."""
    return PopenHandle(proc)


def system_inspector() -> ProcessInspector:
    """The process table of this machine, read with the process environment."""
    return PsProcessInspector(OsEnvironment())


def system_signaller() -> ProcessSignaller:
    """Signals to the processes of this machine."""
    return OsProcessSignaller(system_inspector(), SystemClock())


def system_judge() -> OrphanJudge:
    """The orphan judge over this machine's process table."""
    return PsOrphanJudge(system_inspector())
