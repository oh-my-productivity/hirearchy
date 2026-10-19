"""The data of the run lifecycle: a run in flight, the table of them, what a run is prepared with, how it ended, and the count of runs started."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
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
