"""What a wait compares from look to look (moved from ``progress._snapshot`` and ``_in_progress``)."""

from __future__ import annotations

import re

from ..attention import HumanQueue
from ..kernel import Clock
from ._listing import listed
from ._ports import RootTasks, Snapshot, Snapshots, TaskMark, TaskStates, TaskTeams, TeamLiveness


def moving(snapshot: Snapshot) -> bool:
    """Does any listed task still move? working/waiting always; blocked/stalled while someone below can run."""
    return any(
        m.kind in ("working", "waiting") or (m.kind in ("blocked", "stalled") and tid in snapshot.alive) for tid, m in snapshot.marks.items()
    )


class TeamSnapshots(Snapshots):
    def __init__(self, roots: RootTasks, teams: TaskTeams, states: TaskStates, liveness: TeamLiveness, queue: HumanQueue, clock: Clock) -> None:
        self._roots = roots
        self._teams = teams
        self._states = states
        self._liveness = liveness
        self._queue = queue
        self._clock = clock

    def snapshot(self, task_id: str | None) -> Snapshot:
        tasks = self._roots.tasks()
        results = self._roots.latest_results()
        now = self._clock.now()
        marks: dict[str, TaskMark] = {}
        alive: set[str] = set()
        for t in tasks:
            if (task_id and t.id != task_id) or (not task_id and not listed(results.get(t.id), now)):
                continue
            team = self._teams.team_of(t)
            state = self._states.state_of(t, results.get(t.id), team).state
            marks[t.id] = TaskMark(re.split(r"[ :(]", state, 1)[0], t.title, state)
            if self._liveness.alive(team):
                alive.add(t.id)
        return Snapshot(marks, dict(self._queue.items()), frozenset(alive))
