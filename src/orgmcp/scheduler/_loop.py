"""The heartbeat loop: acquire, pass after pass, release."""

from __future__ import annotations

from collections.abc import Sequence

from ..attention import Waiting
from ..kernel import Clock
from ..settings import OrgSettings
from ._ports import ExitPolicy, Lifecycle, Pacing, SchedulerSession, TickPhase, WorkLeft
from ._run import LoopState
from .api import SchedulerLoop


class PollPacing(Pacing):
    def __init__(self, settings: OrgSettings, clock: Clock) -> None:
        raise NotImplementedError("red: D-sched-2")

    def pause(self) -> None:
        raise NotImplementedError("red: D-sched-2")


class HeartbeatLoop(SchedulerLoop):
    def __init__(
        self, session: SchedulerSession, phases: Sequence[TickPhase], lifecycle: Lifecycle, work: WorkLeft, exits: ExitPolicy, pacing: Pacing,
        state: LoopState,
    ) -> None:
        raise NotImplementedError("red: D-sched-2")

    @property
    def state(self) -> LoopState:
        raise NotImplementedError("red: D-sched-2")

    def acquire(self) -> None:
        raise NotImplementedError("red: D-sched-2")

    def release(self) -> None:
        raise NotImplementedError("red: D-sched-2")

    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run_once(self, max_runs: int | None = None) -> None:
        raise NotImplementedError("red: D-sched-2")

    def tick(self, max_runs: int | None = None) -> bool:
        raise NotImplementedError("red: D-sched-2")

    def finished(self, max_runs: int | None = None) -> bool:
        raise NotImplementedError("red: D-sched-2")

    def waiting_on_user(self, max_runs: int | None = None) -> Waiting | None:
        raise NotImplementedError("red: D-sched-2")

    def reap(self) -> None:
        raise NotImplementedError("red: D-sched-2")

    def start(self, addr: str) -> None:
        raise NotImplementedError("red: D-sched-2")
