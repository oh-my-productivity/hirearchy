"""The runs of the views: one record per run log, completed with the events of the run. (RED: skeleton.)"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..agents import AgentDirectory
from ..eventlog import EventReader
from ..kernel import JsonObject
from ..mail import MailboxReader
from ..runs import RunLogReader, RunRegistry
from ._ports import RunCollection


@dataclass
class RunRec:
    agent: str
    run: str  # <agent>@<log stem>
    start: datetime
    outcome: str = "unknown"  # ok | failed | timeout | killed | running | unknown
    ok: bool | None = None
    end: datetime | None = None
    duration_ms: float | None = None
    exit_code: int | None = None
    error: str | None = None
    batch: list[str] | None = None
    traces: list[str] | None = None
    queue_ms: float | None = None
    source: str = "log"  # log | events
    log: Path | None = None
    pid: int | None = None


def run_dict(run: RunRec) -> JsonObject:
    raise NotImplementedError("red: C-obs-1")


def run_events(evs: Iterable[JsonObject | tuple[datetime, JsonObject]]) -> dict[str, dict[str, JsonObject]]:
    raise NotImplementedError("red: C-obs-1")


class RunCollector(RunCollection):
    def __init__(self, logs: RunLogReader, registry: RunRegistry, agents: AgentDirectory, mailbox: MailboxReader, events: EventReader) -> None:
        self._logs, self._registry, self._agents, self._mailbox, self._events = logs, registry, agents, mailbox, events

    def collect(
        self, since: datetime | None, until: datetime | None, events: Mapping[str, Mapping[str, JsonObject]] | None = None,
        agents: Sequence[str] | None = None,
    ) -> list[RunRec]:
        raise NotImplementedError("red: C-obs-1")

    def team_runs(
        self, team: Sequence[str], in_windows: Callable[[str], bool], events: Mapping[str, Mapping[str, JsonObject]]
    ) -> list[RunRec]:
        raise NotImplementedError("red: C-obs-1")
