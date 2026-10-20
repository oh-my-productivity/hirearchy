"""Runtime fields of the ``scheduler`` entry point (ARCHITECTURE.md 6.2: ``scheduler_factory``)."""

from __future__ import annotations

from dataclasses import dataclass

STEP: str | None = "D-sched-2"  # set to the step's name when the step fills this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "SchedulerLoop": (
        "a scheduler is made per use, over a runtime, with what is its own - its output, its command builder, the cadence clock, the table of runs, the "
        "count of runs started: app.wire_scheduler.loop_of(runtime, ...) (a factory, not a port every runtime has)"
    ),
}


@dataclass(frozen=True)
class Fields:
    """No field: the loop is built by ``wire_scheduler.loop_of`` over the ports of a runtime."""
