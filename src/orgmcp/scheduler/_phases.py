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
    """The failure counts drive pausing; a wrong-shaped ledger would raise inside ``record_failure``."""

    def __init__(self, counter: FailureCounter, console: Console) -> None:
        self._counter, self._console = counter, console

    def run(self, standing: Standing, max_runs: int | None) -> None:
        if self._counter.repair():
            self._console.say("repaired malformed .runtime/failures.json")


class ReapPhase(TickPhase):
    """Collect the runs that ended, ran out of time or lost their agent."""

    def __init__(self, reaper: RunReaper) -> None:
        self._reaper = reaper

    def run(self, standing: Standing, max_runs: int | None) -> None:
        self._reaper.reap(standing.runs)


class OrphanCheck(TickPhase):
    """While some agent is blocked by an orphaned run that could not be dealt with, look at the orphans again."""

    def __init__(self, settler: OrphanSettler) -> None:
        self._settler = settler

    def run(self, standing: Standing, max_runs: int | None) -> None:
        if standing.blocked:
            self._settler.settle(standing.runs, standing.blocked)


class FundedResume(TickPhase):
    """Lift a budget pause once budget is back (a refund note arrives without waking anyone)."""

    def __init__(self, agents: AgentDirectory, pauses: PauseStore, budgets: BudgetQuery, console: Console) -> None:
        self._agents, self._pauses, self._budgets, self._console = agents, pauses, budgets, console

    def run(self, standing: Standing, max_runs: int | None) -> None:
        for addr in self._agents.agents():
            if self._pauses.paused(addr) == "budget" and (self._budgets.budget(addr) or 0) > 0:
                self._pauses.resume(addr, "budget is back", "runtime")
                self._console.say(f"{addr}: budget is back, resumed")


class RunLaunch(TickPhase):
    """Start runs while the cap on runs started allows another."""

    def __init__(self, starter: RunStarter) -> None:
        self._starter = starter

    def run(self, standing: Standing, max_runs: int | None) -> None:
        if standing.can_start:
            self._starter.launch(standing.runs, standing.blocked, max_runs)


class StallCheck(TickPhase):
    """Climb the escalation ladder for every open task whose assignee has gone quiet."""

    def __init__(self, ladder: StallLadder, console: Console) -> None:
        self._ladder, self._console = ladder, console

    def run(self, standing: Standing, max_runs: int | None) -> None:
        for line in self._ladder.check():
            self._console.say(line)


class ReviewCheck(TickPhase):
    """Start a health review when one is due, by the cadence clock."""

    def __init__(self, reviewer: HealthReviewer, clock: Clock, console: Console) -> None:
        self._reviewer, self._clock, self._console = reviewer, clock, console

    def run(self, standing: Standing, max_runs: int | None) -> None:
        done = self._reviewer.review_if_due(self._clock.now())
        if done and done.notes:
            self._console.say(f"health review: {done.flagged} flagged, told {', '.join(n.to for n in done.notes)}")


class GuardedPhase(TickPhase):
    """A best-effort phase: a fault in it is the guard's to log, and never stops the pass."""

    def __init__(self, name: str, phase: TickPhase, guard: PhaseGuard) -> None:
        self.name = name
        self._phase, self._guard = phase, guard

    def run(self, standing: Standing, max_runs: int | None) -> None:
        self._guard.guard(self.name, lambda: self._phase.run(standing, max_runs))
