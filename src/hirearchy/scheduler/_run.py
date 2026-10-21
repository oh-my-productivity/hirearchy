"""The data of the scheduler: a run in flight, the table of them, what a run is prepared with, how it ended, the count of runs started, and what the loop
owns and its collaborators remember."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..kernel import Message
from ..processes import ProcessHandle
from ..runs import RunLogSink


@dataclass
class RunRecord:
    """One run in flight (the former ``scheduler.Run``)."""

    addr: str
    proc: ProcessHandle
    log: Path
    logf: RunLogSink
    started: float  # by the run clock
    batch: int
    strays: dict[str, float] | None = None  # paths of the agent's workspace that could hold stray org files, before the run
    run_id: str = ""  # "<agent>@<run log stem>": the id events and the agent's MCP server (ORG_RUN_ID) carry
    traces: tuple[str, ...] = ()  # distinct traces of the batch
    budget_before: int | None = None
    killed: bool = False
    timed_out: bool = False


RunTable = dict[str, RunRecord]  # agent -> its run in flight; the loop owns it, the starter fills it and the reaper empties it


@dataclass(frozen=True)
class PreparedRun:
    """A run whose batch is taken, whose log exists (and consumes the run of budget) and whose prompt is written, before the process starts."""

    addr: str
    batch: Sequence[Message]
    budget_before: int | None  # before the log exists: that is what consumes the run
    log: Path
    sink: RunLogSink
    run_id: str
    traces: tuple[str, ...]
    prompt: str


@dataclass(frozen=True)
class Exit:
    """How a run in flight ended: its exit code, and the reason when the scheduler ended it (timed out, agent retired)."""

    code: int
    why: str | None = None


@dataclass
class RunCount:
    """How many runs this scheduler has started (the cap ``--max-runs`` counts them; a failed start counts)."""

    total: int = 0


# ------------------------------------------------------------------------------ the loop's own data


@dataclass(frozen=True)
class StopWhen:
    """When a serving scheduler may stop by itself: ``idle`` (nothing left to start or to wait for) and/or ``done`` (nothing left for the user's tasks)."""

    idle: bool = False
    done: bool = False


@dataclass(frozen=True)
class Standing:
    """How things stand when a question is asked of the loop: the runs in flight, the agents whose orphaned run may still live (both are the loop's own,
    live objects) and whether the cap on runs started (``max_runs``) allows another."""

    runs: RunTable
    blocked: set[str]
    can_start: bool = True


@dataclass
class LoopState:
    """What the loop owns: the table of runs in flight, the agents blocked by an orphan, the count of runs started, and how it is running."""

    runs: RunTable = field(default_factory=dict)
    blocked: set[str] = field(default_factory=set)
    count: RunCount = field(default_factory=RunCount)
    mode: str = "daemon"  # daemon | until_done | until_idle | once (for the scheduler.start event)
    max_runs: int | None = None
    exit_reason: str = "stopped"


@dataclass
class GraceMemory:
    """Until-done: since when nothing can progress without the user (by the cadence clock)."""

    since: float | None = None


@dataclass
class UpkeepMemory:
    """When the heartbeat was last sent and the event log last pruned (by the cadence clock)."""

    heartbeat_at: float | None = None
    pruned_at: float | None = None


@dataclass
class GuardMemory:
    """What the guard has already said: the last error of each phase, and when the last one was recorded as an event."""

    errors: dict[str, str] = field(default_factory=dict)
    emitted: dict[str, tuple[str, float]] = field(default_factory=dict)


@dataclass
class LoopMemory:
    """What the collaborators of the loop remember from one tick to the next. It is data apart from them so that a loop rebuilt over another runtime
    (a test does, when it replaces the runtime under a running scheduler) goes on where the old one was."""

    grace: GraceMemory = field(default_factory=GraceMemory)
    upkeep: UpkeepMemory = field(default_factory=UpkeepMemory)
    guard: GuardMemory = field(default_factory=GuardMemory)
    stall_views: object | None = None  # the memo of the task views of the stall ladder: the wiring keeps it here (the scheduler does not look into it)
