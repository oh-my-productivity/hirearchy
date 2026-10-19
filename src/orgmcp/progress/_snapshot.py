"""What a wait compares from look to look (moved from ``progress._snapshot``)."""

from __future__ import annotations

from ..attention import HumanQueue
from ..kernel import Clock
from ._ports import RootTasks, Snapshot, Snapshots, TaskStates, TaskTeams, TeamLiveness


def moving(snapshot: Snapshot) -> bool:
    """Does any listed task still move? working/waiting always; blocked/stalled while someone below can run."""
    raise NotImplementedError("red: C-progress")


class TeamSnapshots(Snapshots):
    def __init__(self, roots: RootTasks, teams: TaskTeams, states: TaskStates, liveness: TeamLiveness, queue: HumanQueue, clock: Clock) -> None:
        self._roots = roots
        self._teams = teams
        self._states = states
        self._liveness = liveness
        self._queue = queue
        self._clock = clock

    def snapshot(self, task_id: str | None) -> Snapshot:
        raise NotImplementedError("red: C-progress")
