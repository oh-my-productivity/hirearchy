"""When a serving scheduler stops by itself: idle, finished, or waiting on the user for longer than the grace period."""

from __future__ import annotations

from ..daemon import FINISHED, ExitMarker
from ..kernel import Clock
from ..settings import OrgSettings
from ._ports import Console, ExitPolicy, WaitGrace, WorkLeft
from ._run import GraceMemory, Standing, StopWhen


class GraceWait(WaitGrace):
    """Until-done: the exit reason once nothing has been able to progress without the user for the grace period (``until_done_grace_seconds``), else ''.
    Anything that changes the picture (a grant, a resume, a new task) starts the count again. A task that is merely stalled also waits for the stall
    ladder to reach root."""

    def __init__(self, work: WorkLeft, settings: OrgSettings, clock: Clock, console: Console, memory: GraceMemory) -> None:
        self._work, self._settings, self._clock, self._console, self._memory = work, settings, clock, console, memory

    def check(self, standing: Standing) -> str:
        waiting = self._work.waiting(standing)
        if waiting is None:
            self._memory.since = None
            return ""
        now = self._clock.time()
        if self._memory.since is None:
            self._memory.since = now
            self._console.say(f"{waiting.text}. Exiting in {self._settings.number('until_done_grace_seconds'):.0f}s "
                              "unless something changes")
        if not waiting.settled or now - self._memory.since < self._settings.number("until_done_grace_seconds"):
            return ""
        return waiting.text


class GraceExitPolicy(ExitPolicy):
    """After a pass: an idle scheduler (``until_idle``) stops when nothing is active; an until-done one when everything is finished, or when nothing can
    progress without the user for the grace period. The reason of the last two is left in the exit marker, where ``hirearchy status`` finds it."""

    def __init__(self, work: WorkLeft, grace: WaitGrace, marker: ExitMarker, console: Console) -> None:
        self._work, self._grace, self._marker, self._console = work, grace, marker, console

    def after_tick(self, stop: StopWhen, active: bool, standing: Standing) -> str | None:
        if stop.idle and not active:
            self._console.say("organization is idle")
            return "idle: nothing left to do"
        if stop.done and self._work.finished(standing):
            self._console.say(f"scheduler exiting: {FINISHED}")
            self._marker.write(FINISHED)
            return FINISHED
        if stop.done and (reason := self._grace.check(standing)):
            self._console.say(f"scheduler exiting: {reason}")
            self._marker.write(reason)
            return reason
        return None
