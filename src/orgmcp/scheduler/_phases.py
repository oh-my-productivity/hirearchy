"""The steps of a pass of the loop, in the order wiring puts them: each is a small class of its own."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..eligibility import FailureCounter, PauseStore
from ..kernel import Clock
from ..review import HealthReviewer
from ..stalls import StallLadder
from ._ports import Console, OrphanSettler, PhaseGuard, RunReaper, RunStarter, TickPhase
from ._run import Standing


class FailureLedgerRepair(TickPhase):
    def __init__(self, counter: FailureCounter, console: Console) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")


class ReapPhase(TickPhase):
    def __init__(self, reaper: RunReaper) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")


class OrphanCheck(TickPhase):
    def __init__(self, settler: OrphanSettler) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")


class FundedResume(TickPhase):
    def __init__(self, agents: AgentDirectory, pauses: PauseStore, budgets: BudgetQuery, console: Console) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")


class RunLaunch(TickPhase):
    def __init__(self, starter: RunStarter) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")


class StallCheck(TickPhase):
    def __init__(self, ladder: StallLadder, console: Console) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")


class ReviewCheck(TickPhase):
    def __init__(self, reviewer: HealthReviewer, clock: Clock, console: Console) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")


class GuardedPhase(TickPhase):
    def __init__(self, name: str, phase: TickPhase, guard: PhaseGuard) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")
