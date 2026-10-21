"""The guard of the best-effort phases: a fault in one is logged once and never stops the loop."""

from __future__ import annotations

from collections.abc import Callable

from ..kernel import Clock, EventSink, clip
from ._events import ERROR_MAX
from ._ports import Console, PhaseGuard
from ._run import GuardMemory


class LoggingPhaseGuard(PhaseGuard):
    """Runs a phase; an error is said to the operator once per distinct message and recorded as a ``scheduler.error`` event when it changes, then every minute
    (by the cadence clock) while it persists."""

    def __init__(self, console: Console, events: EventSink, clock: Clock, memory: GuardMemory) -> None:
        self._console, self._events, self._clock, self._memory = console, events, clock, memory

    def guard(self, phase: str, fn: Callable[[], None]) -> None:
        """Run a best-effort phase; log (once per distinct error) instead of raising out of the loop."""
        memory = self._memory
        try:
            fn()
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            if memory.errors.get(phase) != message:
                memory.errors[phase] = message
                self._console.say(f"{phase} failed (will retry next tick): {message}")
            last = memory.emitted.get(phase)  # a fault that persists is recorded when it changes, then every minute
            if last is None or last[0] != message or self._clock.time() - last[1] >= 60:
                memory.emitted[phase] = (message, self._clock.time())
                self._events.emit("scheduler.error", phase=phase, error=clip(message, ERROR_MAX))
        else:
            memory.errors.pop(phase, None)
