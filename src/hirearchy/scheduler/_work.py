"""What is left to do, from the standpoint of a scheduler: its own runs and the agents its orphans block count."""

from __future__ import annotations

from ..attention import OpenWork, Waiting, WaitingOnUser
from ..eligibility import RunnableQuery
from ._ports import WorkLeft
from ._run import Standing


class QueriedWork(WorkLeft):
    """The three questions the loop asks about what is left, answered by the ports of ``attention`` and ``eligibility`` with the view of this scheduler."""

    def __init__(self, work: OpenWork, runnable: RunnableQuery, waiting: WaitingOnUser) -> None:
        self._work, self._runnable, self._waiting = work, runnable, waiting

    def remains(self, standing: Standing) -> bool:
        return bool(standing.runs) or (bool(self._runnable.runnable(exclude=set(standing.runs) | standing.blocked)) and standing.can_start)

    def finished(self, standing: Standing) -> bool:
        return self._work.nothing_to_do(running=set(standing.runs), blocked=standing.blocked, can_start=standing.can_start)

    def waiting(self, standing: Standing) -> Waiting | None:
        return self._waiting.analyze(running=set(standing.runs), blocked=standing.blocked, can_start=standing.can_start)
