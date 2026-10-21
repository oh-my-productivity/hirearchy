"""What the dashboard shows, as small data classes (the plain-text forms are properties, ``doc_text`` the one function)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, fmt_dur
from ..reflection import Stats
from ._events import EventLine


@dataclass
class Section:
    title: str
    lines: list[str]
    errors: frozenset[int] = frozenset()  # indexes of the lines that are errors (shown in red)


def doc_text(doc: list[Section]) -> str:
    out: list[str] = []
    for s in doc:
        if s.title:
            out.append(f"## {s.title}")
        out += s.lines
        out.append("")
    return "\n".join(out).rstrip() + "\n"


@dataclass
class AgentRow:
    addr: str
    name: str
    depth: int
    parent: str | None
    role: str
    model: str
    kind: str  # one of STATE_KINDS
    glyph: str
    word: str  # the state in words: "running 1m12s", "queued: no budget", "working on 2 task(s)", ...
    budget: int | None  # runs left (None: unlimited, root)
    unread: int = 0
    open_tasks: int = 0
    delegated: int = 0
    runs_used: int = 0
    paused: str | None = None
    elapsed_s: float | None = None
    reason: str = ""  # why it is queued (see the queue of ``NowQueries``)
    queued_behind: int = 0  # running agent: mail waiting for the next run
    main: str = ""  # ``word`` without the trailing ", N unread" note
    short: str = ""  # ``main`` in fewer characters (the tree uses it when the pane is narrow)
    note: str = ""
    children: list[str] = field(default_factory=list)
    below_running: int = 0
    below_queued: int = 0
    services: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return f"{self.glyph} {self.word}"


@dataclass
class SchedulerView:
    state: str  # running | stopped | unverified
    pid: int | None = None
    since: str | None = None
    mode: str | None = None
    uptime_s: float | None = None
    heartbeat_age_s: float | None = None
    last_exit: str | None = None
    detail: str = ""

    @property
    def text(self) -> str:
        if self.state == "running":
            bits = [b for b in (self.mode, f"up {fmt_dur(self.uptime_s * 1000)}" if self.uptime_s is not None else None) if b]
            if self.heartbeat_age_s is not None:
                bits.append(f"heartbeat {fmt_dur(self.heartbeat_age_s * 1000)} ago")
            return f"scheduler running pid {self.pid}" + (f" ({', '.join(bits)})" if bits else "")
        if self.state == "unverified":
            return f"scheduler unverified (pid {self.pid}: {self.detail})"
        return "scheduler stopped" + (f" ({self.last_exit})" if self.last_exit else "")


@runtime_checkable
class RowLookup(Protocol):
    """Where an agent's row is looked up (a snapshot knows its rows by address)."""

    def row(self, addr: str) -> AgentRow | None: ...


@dataclass
class Snapshot(RowLookup):
    org_name: str
    root: str
    at: datetime
    scheduler: SchedulerView
    max_parallel: int
    agents: dict[str, AgentRow]
    order: list[str]  # root first, then depth-first
    running: int = 0
    queued: int = 0
    needs_you: list[tuple[str, str]] = field(default_factory=list)  # (message id, line)
    errors_15m: int = 0
    last_event: datetime | None = None
    events_seen: bool = False
    bad_files: dict[str, str] = field(default_factory=dict)
    retired: int = 0
    sig: tuple[object, ...] = ()
    ms: float = 0.0

    @property
    def counts_text(self) -> str:
        return (f"running {self.running}/{self.max_parallel} · queued {self.queued} · "
                f"waiting on you {len(self.needs_you)} · errors 15m {self.errors_15m}")

    def row(self, addr: str) -> AgentRow | None:
        return self.agents.get(addr)


@dataclass
class MsgRow:
    id: str
    box: str  # inbox | inflight | read | sent
    type: str
    sender: str
    to: str
    title: str
    status: str | None
    budget: int
    when: datetime | None
    path: Path | None

    @property
    def direction(self) -> str:
        return "out" if self.box == "sent" else "in"


@dataclass
class RunLog:
    path: Path | None = None
    rel: str = ""
    running: bool = False
    header: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    truncated: bool = False  # lines were dropped from the start
    size: int = 0
    stamp: tuple[object, ...] = ()
    note: str = ""


@dataclass
class AgentDetail:
    addr: str
    row: AgentRow | None
    overview: list[Section]
    messages: list[MsgRow]
    runlog: RunLog
    memory: str
    charter: str
    events: list[JsonObject]
    activity: list[EventLine] = field(default_factory=list)  # ``events`` as lines (readable, or raw when asked)


@dataclass
class RequestRow:
    id: str
    title: str
    assignee: str
    service: str | None
    revises: str | None
    state: str  # the full state text of ``progress`` ("working", "waiting on ceo/eng", "blocked: ...")
    klass: str  # working | waiting | stalled | blocked | done | failed
    who: str
    runs_used: int
    runs_given: int
    runs_text: str
    last_activity_s: float | None
    created: datetime | None
    needs_you: int
    artifacts: list[str] = field(default_factory=list)


@dataclass
class ServiceRow:
    owner: str
    name: str
    contract_version: int
    playbook_version: int
    locked: bool
    stats: Stats
    playbook_reason: str
    description: str


@dataclass
class HealthView:
    now_text: str
    flagged: list[tuple[str, list[tuple[str, str]]]]  # (agent, [(flag, why)])
    summary: str
    at: datetime
