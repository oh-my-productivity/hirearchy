"""The heartbeat loop: acquire, pass after pass, release."""

from __future__ import annotations

import signal
from collections.abc import Sequence

from ..attention import Waiting
from ..kernel import Clock
from ..settings import OrgSettings
from ._ports import ExitPolicy, Lifecycle, Pacing, SchedulerSession, TickPhase, WorkLeft
from ._run import LoopState, Standing, StopWhen
from .api import SchedulerLoop


class PollPacing(Pacing):
    """Waits ``poll_seconds`` on its clock."""

    def __init__(self, settings: OrgSettings, clock: Clock) -> None:
        self._settings, self._clock = settings, clock

    def pause(self) -> None:
        self._clock.sleep(self._settings.number("poll_seconds"))


class HeartbeatLoop(SchedulerLoop):
    """Wakes an agent for one fresh, short run whenever its inbox has messages: ``tick`` is one pass over the ``phases``; ``serve`` acquires the
    organization, passes until told (or the exit policy says) to stop, and releases. It owns the table of runs in flight, the agents blocked by an
    orphan, the count of runs started and how it runs (``state``)."""

    def __init__(
        self, session: SchedulerSession, phases: Sequence[TickPhase], lifecycle: Lifecycle, work: WorkLeft, exits: ExitPolicy, pacing: Pacing,
        state: LoopState,
    ) -> None:
        self._session, self._phases, self._lifecycle, self._work, self._exits, self._pacing = session, tuple(phases), lifecycle, work, exits, pacing
        self._state = state

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def phases(self) -> tuple[TickPhase, ...]:
        return self._phases

    def _standing(self, max_runs: int | None) -> Standing:
        s = self._state
        return Standing(s.runs, s.blocked, max_runs is None or s.count.total < max_runs)

    # ------------------------------------------------------------- lifecycle

    def acquire(self) -> None:
        s = self._state
        self._session.open(s.mode, s.max_runs, s.runs, s.blocked)

    def release(self) -> None:
        s = self._state
        self._session.close(s.exit_reason, s.runs, s.count.total)

    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        s = self._state
        s.mode = "until_done" if until_done else "until_idle" if until_idle else "daemon"
        s.max_runs = max_runs
        self.acquire()
        stop = False

        def on_signal(*_: object) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGTERM, on_signal)
        try:
            while not stop:
                active = self.tick(max_runs=max_runs)
                reason = self._exits.after_tick(StopWhen(until_idle, until_done), active, self._standing(max_runs))
                if reason is not None:
                    s.exit_reason = reason
                    break
                self._pacing.pause()
            else:
                s.exit_reason = "stopped by SIGTERM"
        except KeyboardInterrupt:
            s.exit_reason = "interrupted (KeyboardInterrupt)"
        except Exception as exc:
            s.exit_reason = f"error: {type(exc).__name__}: {exc}"
            raise
        finally:
            self.release()

    def run_once(self, max_runs: int | None = None) -> None:
        s = self._state
        s.mode, s.max_runs, s.exit_reason = "once", max_runs, "once: one pass done"
        self.acquire()
        try:
            self.tick(max_runs=max_runs)
            while s.runs:
                self._pacing.pause()
                self.reap()
        finally:
            self.release()

    # ------------------------------------------------------------------ tick

    def tick(self, max_runs: int | None = None) -> bool:
        """One pass: reap finished runs, start new ones, detect stalls, review health. Returns True if work remains."""
        standing = self._standing(max_runs)
        for phase in self._phases:
            phase.run(standing, max_runs)
        return self._work.remains(self._standing(max_runs))

    def finished(self, max_runs: int | None = None) -> bool:
        """Is there nothing left for this scheduler: root has no open task, no run is in flight, no agent could start?"""
        return self._work.finished(self._standing(max_runs))

    def waiting_on_user(self, max_runs: int | None = None) -> Waiting | None:
        """Is every open root task unable to progress without the user (with this scheduler's own view of what runs)? Read-only."""
        return self._work.waiting(self._standing(max_runs))

    def reap(self) -> None:
        self._lifecycle.reaper.reap(self._state.runs)

    def start(self, addr: str) -> None:
        self._lifecycle.starter.start(self._state.runs, addr)
