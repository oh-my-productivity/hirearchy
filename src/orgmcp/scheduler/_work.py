"""What is left to do, from the standpoint of a scheduler: its own runs and the agents its orphans block count."""

from __future__ import annotations

from ..attention import OpenWork, Waiting, WaitingOnUser
from ..eligibility import RunnableQuery
from ._ports import WorkLeft
from ._run import Standing


class QueriedWork(WorkLeft):
    def __init__(self, work: OpenWork, runnable: RunnableQuery, waiting: WaitingOnUser) -> None:
        raise NotImplementedError("red: D-sched-2")

    def remains(self, standing: Standing) -> bool:
        raise NotImplementedError("red: D-sched-2")

    def finished(self, standing: Standing) -> bool:
        raise NotImplementedError("red: D-sched-2")

    def waiting(self, standing: Standing) -> Waiting | None:
        raise NotImplementedError("red: D-sched-2")
