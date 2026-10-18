"""Data layer of the terminal dashboard (``orgmcp dash``): pure, UI-free snapshots of an organization.

Everything here is *derived from the files*, with the same functions ``status`` / ``progress`` / ``observe`` use
(``Org.running/unread/paused/budget/open_tasks/outstanding``, ``progress._state/_runs/_last_activity/_human_items``,
``observe.trace/now_view/check/events``, ``services.cases/summarize/stats_by_version``, ``health.org_health``), so the
dashboard cannot disagree with them. Nothing is written inside the organization and no event is emitted.

What is added on top is only what a screen that refreshes every second needs:

* :class:`LenientOrg` - an :class:`~orgmcp.core.Org` that skips a message or charter that does not parse (and
  remembers it in ``bad``) instead of raising, and caches the parsed mailboxes by directory mtime, so a tick of an
  organization with thousands of messages only re-reads the mailboxes that changed;
* :class:`EventFeed` - the event log kept in memory and extended incrementally (``observe.Follower``);
* :class:`DashData` - ``snapshot`` (header counts, the agent tree with exact state words), ``agent_detail``,
  ``requests``, ``services``, ``health``, ``trace_text`` ... each returning small dataclasses or plain text.

Every function tolerates what a live system produces: no events directory, no agents, a scheduler that is not running,
retired agents, files that are being written, a message that fails to parse.
"""

from __future__ import annotations

import os
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import core, observe, progress as prog, services
from .app import wire_agents
from .core import BOXES, DEFAULT_CONFIG, ROOT, Message, Org, OrgError, _visible, latest_results, split_frontmatter
from .dashboard_events import EventLine, describe, event_lines
from .health import _aware, _stamp, config_number, org_health
from .observe import fmt_dur
from .scheduler import EXIT_FILE, SchedulerState, scheduler_state

ERROR_WINDOW = timedelta(minutes=15)
ERROR_WINDOW_TEXT = "15m"
LOG_LINES = 2000  # lines of a run log that are shown (the tail)
LOG_BYTES = 1_000_000  # never read more than this from the end of a run log
FEED_KEEP = 5000  # events kept in memory
FEED_BACKFILL = "2h"  # how far back the first load of the event feed reaches
TEXT_CAP = 60_000  # characters of a memory file / message shown
CACHE_TRUST = 2.0  # a directory modified less than this many seconds before it was listed is listed again next time
SERVICES_TTL = 5.0
HEALTH_TTL = 8.0
REQUESTS_TTL = 5.0

STATE_KINDS = ("running", "queued", "working", "waiting", "idle", "paused", "budget", "you")
GLYPHS = {"running": "▶", "queued": "◔", "working": "◆", "waiting": "◇", "idle": "○", "paused": "‖",
          "budget": "!", "you": "★"}

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|\x1b\].*?(?:\x07|\x1b\\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(text: str) -> str:
    """Terminal-safe text: no ANSI escapes, no control characters, carriage-return progress lines reduced to their end."""
    text = _ANSI.sub("", text)
    if "\r" in text:
        text = "\n".join(line.rsplit("\r", 1)[-1] for line in text.replace("\r\n", "\n").split("\n"))
    return _CONTROL.sub("", text)


def _now() -> datetime:
    return core.utcnow()


# ================================================================================================ the lenient Org


class LenientOrg(Org):
    """An Org that keeps going: unreadable messages and charters are skipped (listed in :attr:`bad`), parsed mailboxes
    are cached per directory mtime (a box that did not change is not read again), ORG.md is parsed once per change."""

    def __init__(self, root: str | Path):
        super().__init__(root)
        self._box_cache: dict[tuple[str, str], tuple[int, bool, list[Message]]] = {}
        self._bad_boxes: dict[tuple[str, str], dict[str, str]] = {}
        self._cfg: tuple[tuple[int, int], dict] | None = None
        self._bad_misc: dict[str, str] = {}
        self._merged: dict[tuple, tuple[list, list[Message]]] = {}
        self._runs_cache: dict[str, tuple[int, bool, int]] = {}
        self._stat_memo: dict[tuple[str, str], int] = {}
        self._pause_cache: dict[str, tuple[int, str | None]] = {}
        self._root_s = str(self.root)
        # the caching of the agent tree and the reading of charters (reported in ``bad``) are the decorators of the agents package
        self.runtime = wire_agents.lenient(self.runtime, self, self._bad_misc)

    @property
    def bad(self) -> dict[str, str]:
        """Files that could not be read: path (relative to the org) -> why."""
        out = dict(self._bad_misc)
        for d in self._bad_boxes.values():
            out.update(d)
        return out

    # -- one stat per directory per tick
    def tick(self) -> None:
        """Start a new refresh: directory mtimes are looked at again (within one refresh each is stat'ed once)."""
        self._stat_memo.clear()

    def mtime(self, addr: str, name: str) -> int:
        """mtime_ns of ``<addr>/<name>`` (-1: missing), stat'ed at most once per tick. ``name`` "" is the agent dir."""
        a = self.norm(addr)
        key = (a, name)
        v = self._stat_memo.get(key)
        if v is None:
            path = self._root_s if a == ROOT else os.path.join(self._root_s, a)
            try:
                v = os.stat(os.path.join(path, name) if name else path).st_mtime_ns
            except OSError:
                v = -1
            self._stat_memo[key] = v
        return v

    def paused(self, addr: str) -> str | None:
        a = self.norm(addr)
        m = self.mtime(a, ".paused")
        if m < 0:
            return None
        hit = self._pause_cache.get(a)
        if hit is not None and hit[0] == m:
            return hit[1]
        value = super().paused(a)
        self._pause_cache[a] = (m, value)
        return value

    # -- messages
    def messages(self, addr: str, *boxes: str) -> list[Message]:
        key = (self.norm(addr), boxes)
        lists = [self._box(addr, box) for box in boxes]
        hit = self._merged.get(key)
        if hit is not None and len(hit[0]) == len(lists) and all(a is b for a, b in zip(hit[0], lists)):
            return hit[1]
        merged = sorted((m for lst in lists for m in lst), key=lambda m: m.id)
        self._merged[key] = (lists, merged)
        return merged

    def _trusted(self, listed_at: int, mtime: int) -> bool:
        """A listing is reused only if the directory had been quiet for a while when it was made (coarse-mtime safe)."""
        return (listed_at - mtime) > CACHE_TRUST * 1e9

    def _box(self, addr: str, box: str) -> list[Message]:
        key = (self.norm(addr), box)
        mtime = self.mtime(addr, box)
        if mtime < 0:
            self._box_cache.pop(key, None)
            self._bad_boxes.pop(key, None)
            return []
        hit = self._box_cache.get(key)
        if hit is not None and hit[0] == mtime and hit[1]:
            return hit[2]
        d = self.dir(addr) / box
        listed_at = time.time_ns()
        previous = {m.path.name: m for m in hit[2] if m.path is not None} if hit is not None else {}
        out: list[Message] = []
        bad: dict[str, str] = {}
        try:
            names = sorted(e.name for e in os.scandir(d) if e.name.endswith(".md") and not e.name.startswith("."))
        except OSError:
            names = []
        for n in names:
            old = previous.get(n)
            if old is not None:  # messages are immutable: a file seen before is the same message
                out.append(old)
                continue
            p = d / n
            try:
                out.append(Message.load(p))
            except FileNotFoundError:
                continue  # moved between the listing and the read: the next tick sees it where it went
            except Exception as exc:  # noqa: BLE001 - yaml errors, bad numbers, bad encoding, ...
                bad[self._rel(p)] = f"{type(exc).__name__}: {str(exc).splitlines()[0][:80] if str(exc) else ''}".rstrip(": ")
        if hit is not None and len(out) == len(hit[2]) and all(a is b for a, b in zip(out, hit[2])):
            out = hit[2]  # unchanged: the same list object, so everything derived from it stays valid
        self._box_cache[key] = (mtime, self._trusted(listed_at, mtime), out)
        if bad:
            self._bad_boxes[key] = bad
        else:
            self._bad_boxes.pop(key, None)
        return out

    def _bad_in(self, addr: str, box: str) -> int:
        return len(self._bad_boxes.get((self.norm(addr), box), ()))

    def unread(self, addr: str) -> int:
        """Inbox messages that wake the agent (an unreadable file still counts as mail, like in ``Org.unread``)."""
        msgs = self._box(addr, "inbox")
        return sum(1 for m in msgs if m.wake) + self._bad_in(addr, "inbox")

    def running(self, addr: str) -> bool:
        return bool(self._box(addr, "inflight")) or self._bad_in(addr, "inflight") > 0

    def runs_used(self, addr: str) -> int:
        mtime = self.mtime(addr, "runs")
        if mtime < 0:
            return 0
        key = self.norm(addr)
        hit = self._runs_cache.get(key)
        if hit is not None and hit[0] == mtime and hit[1]:
            return hit[2]
        listed_at = time.time_ns()
        n = super().runs_used(addr)
        self._runs_cache[key] = (mtime, self._trusted(listed_at, mtime), n)
        return n

    def _rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return str(p)

    # -- config
    @property
    def config(self) -> dict:
        p = self.root / "ORG.md"
        try:
            st = p.stat()
            stamp = (st.st_mtime_ns, st.st_size)
            if self._cfg is not None and self._cfg[0] == stamp:
                return self._cfg[1]
            meta, _ = split_frontmatter(p.read_text(encoding="utf-8"))
            cfg = {**DEFAULT_CONFIG, **(meta if isinstance(meta, dict) else {})}
            self._cfg = (stamp, cfg)
            self._bad_misc.pop("ORG.md", None)
            return cfg
        except Exception as exc:  # noqa: BLE001
            self._bad_misc["ORG.md"] = type(exc).__name__
            return dict(DEFAULT_CONFIG)


# ================================================================================================ agent states


@dataclass(frozen=True)
class AgentState:
    """The one state of an agent, in words. ``main`` + ``note`` is the whole text (``word``); the tree may shorten
    ``main`` to fit and always keeps ``note`` (the mail waiting)."""

    kind: str  # one of STATE_KINDS
    main: str
    note: str = ""
    reason: str = ""  # why mail waits (running: for the next run; queued: why it does not run yet)
    short: str = ""  # ``main`` in fewer characters, for a narrow tree (empty: no shorter form)

    @property
    def word(self) -> str:
        return self.main + self.note


def pause_text(paused: str) -> str:
    """'paused: <reason>' - without saying 'paused' twice when the reason already does ('paused by the user: ...')."""
    return paused if paused.lower().startswith("paused") else f"paused: {paused}"


def classify(*, running: bool, unread: int, paused: str | None, budget: int, open_tasks: int, delegated: int,
             scheduler_up: bool, free_slots: int, max_parallel: int, elapsed_s: float | None = None) -> AgentState:
    """The state of one agent. Exactly one applies, in this precedence (an agent is never two of them):

    1. running - a run is in flight (mail that arrived meanwhile waits for the next run; a pause is noted);
    2. paused - ``paused: <reason>`` (+ ``N unread``): a paused agent is not started, whatever else is true;
    3. out of budget - no runs left (``out of budget`` + ``N unread``): it is not started either;
    4. queued - it has mail, may run, and has not started yet - the reason says why: the scheduler is not running,
       all ``max_parallel`` slots are busy, or it starts on the next tick;
    5. waiting on its reports / working on tasks / idle.

    A ``budget`` pause with budget granted since is no pause (the scheduler starts such an agent)."""
    pause = paused if (paused and not (paused == "budget" and budget > 0)) else None
    if running:
        main = "running" + (f" {fmt_dur(elapsed_s * 1000)}" if elapsed_s is not None else "")
        if not scheduler_up:
            main += " (scheduler not running)"
        notes = []
        reason = ""
        if unread:
            notes.append(f"+{unread} unread")
            reason = "its current run is still going; the next run starts after it"
        if pause:
            notes.append("then out of budget" if pause == "budget" else "then " + pause_text(pause))
        return AgentState("running", main, "".join(f", {n}" for n in notes), reason)
    if pause and pause != "budget":
        return AgentState("paused", pause_text(pause), f", {unread} unread" if unread else "")
    if pause == "budget" or (budget <= 0 and (unread or open_tasks or delegated)):
        return AgentState("budget", "out of budget", f", {unread} unread" if unread else "")
    if unread:
        if not scheduler_up:
            reason, short = "scheduler is not running", "scheduler off"
        elif free_slots <= 0:
            reason, short = f"max_parallel ({max_parallel}) runs are busy", "all slots busy"
        else:
            reason, short = "ready: starts on the next tick", "next tick"  # the reason has the wording of observe.now_view
        return AgentState("queued", f"queued: {reason.removeprefix('ready: ')}", f", {unread} unread", reason, f"queued: {short}")
    if delegated:
        return AgentState("waiting", f"waiting on {delegated} report(s)")
    if open_tasks:
        return AgentState("working", f"working on {open_tasks} task(s)")
    return AgentState("idle", "idle")


# ================================================================================================ small structures


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
    reason: str = ""  # why it is queued (see observe.now_view)
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


@dataclass
class Snapshot:
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
    sig: tuple = ()
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
    stamp: tuple = ()
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
    events: list[dict]
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
    stats: services.Stats
    playbook_reason: str
    description: str


@dataclass
class HealthView:
    now_text: str
    flagged: list[tuple[str, list[tuple[str, str]]]]  # (agent, [(flag, why)])
    summary: str
    at: datetime


# ================================================================================================ event feed


class EventFeed:
    """The event log in memory: the last ``keep`` events (oldest first), extended by ``observe.Follower`` polls."""

    def __init__(self, org: Org, keep: int = FEED_KEEP, backfill: str = FEED_BACKFILL, now: datetime | None = None):
        self.org = org
        self.keep = keep
        self.events: deque[dict] = deque(maxlen=keep)
        self.errors: deque[tuple[datetime, dict]] = deque()
        self.version = 0
        self.any = False
        self.last_ts: datetime | None = None
        now = _aware(now) or _now()
        self.follower = observe.Follower(org, now=now)  # first: no event can fall between the backlog and the polls
        try:
            view = observe.events_view(org, since=backfill, limit=keep, now=now)
            backlog = view["events"]
            errs = observe.events_view(org, since=ERROR_WINDOW_TEXT, errors=True, now=now)["events"]
        except Exception:  # noqa: BLE001 - a damaged log must not keep the dashboard from starting
            backlog, errs = [], []
        self._seen = {self._key(e) for e in backlog[-400:]}
        for ev in backlog:
            self._add(ev)
        for ev in errs:
            t = observe._ts(ev.get("ts"))
            if t is not None:
                self.errors.append((t, ev))
        self.any = bool(backlog) or bool(observe.event_files(org))

    @staticmethod
    def _key(ev: dict):
        return (ev.get("proc"), ev.get("pid"), ev.get("seq"), ev.get("ts"))

    def _add(self, ev: dict) -> None:
        self.events.append(ev)
        t = observe._ts(ev.get("ts"))
        if t is not None and (self.last_ts is None or t > self.last_ts):
            self.last_ts = t

    def poll(self, now: datetime | None = None) -> int:
        """Read what was appended since the last poll; returns how many events were added."""
        now = _aware(now) or _now()
        try:
            new = self.follower.poll(now=now)
        except Exception:  # noqa: BLE001
            new = []
        added = 0
        for ev in new:
            if self._seen:
                if self._key(ev) in self._seen:
                    continue
            self._add(ev)
            added += 1
            if observe.is_error(ev):
                t = observe._ts(ev.get("ts")) or now
                self.errors.append((t, ev))
        self._seen = set()
        if added:
            self.version += 1
            self.any = True
        cutoff = now - ERROR_WINDOW
        while self.errors and self.errors[0][0] < cutoff:
            self.errors.popleft()
        return added

    def error_count(self, now: datetime) -> int:
        cutoff = now - ERROR_WINDOW
        return sum(1 for t, _ in self.errors if t >= cutoff)

    def matching(self, text: str = "", errors: bool = False, agent: str | None = None, limit: int = 1000) -> list[dict]:
        """The newest ``limit`` events that match, oldest first. ``text``: words, all of which must appear (case
        insensitive) in the agent / kind / trace / run fields; ``agent``: only events of that agent."""
        words = [w.lower() for w in text.split()]
        match = observe._matcher(agent=agent, errors=errors) if (agent or errors) else None
        out: list[dict] = []
        for ev in reversed(self.events):
            if match is not None and not match(ev):
                continue
            if words:
                hay = " ".join(str(x) for x in (ev.get("kind"), ev.get("actor"), ev.get("agent"), ev.get("from"), ev.get("to"),
                                                ev.get("trace"), ev.get("run"), ev.get("tool"), *(ev.get("traces") or ()),
                                                describe(ev))  # what the readable line says: 'refused', a title, ...
                               if x not in (None, "")).lower()
                if not all(w in hay for w in words):
                    continue
            out.append(ev)
            if len(out) >= limit:
                break
        out.reverse()
        return out


# ================================================================================================ the data object


def _mtime(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


class DashData:
    """Everything the dashboard shows, with the caches that keep a refresh tick cheap. Not thread-safe: use it from one
    thread at a time (the app serialises its refreshes)."""

    def __init__(self, root: str | Path, now: Callable[[], datetime] | None = None, scheduler_ttl: float = 3.0):
        self.org = LenientOrg(root)
        self._clock = now
        self.scheduler_ttl = scheduler_ttl
        self.feed: EventFeed | None = None
        self.snap: Snapshot | None = None
        self._sched: tuple[float, SchedulerView] | None = None
        self._sched_files: dict[Path, tuple[tuple, dict]] = {}
        self._memo: dict[str, tuple[tuple, float, object]] = {}
        self._logs: dict[Path, tuple[tuple, RunLog]] = {}
        self._texts: dict[Path, tuple[tuple, str]] = {}
        self._msg_index: dict[str, tuple[list, dict]] = {}
        self.check_result: tuple[datetime, str, bool] | None = None

    # ---------------------------------------------------------------------------------------- time and memo
    def now(self) -> datetime:
        return _aware(self._clock()) if self._clock else _now()

    def _memoised(self, name: str, sig: tuple, ttl: float, fn: Callable[[], object]):
        hit = self._memo.get(name)
        if hit is not None and hit[0] == sig and time.monotonic() - hit[1] < ttl:
            return hit[2]
        value = fn()
        self._memo[name] = (sig, time.monotonic(), value)
        return value

    # ---------------------------------------------------------------------------------------- snapshot
    def snapshot(self) -> Snapshot:
        t0 = time.perf_counter()
        org, now = self.org, self.now()
        org.tick()
        if self.feed is None:
            self.feed = EventFeed(org, now=now)
        else:
            self.feed.poll(now)
        agents = org.agents()
        cfg = org.config
        max_parallel = config_number(cfg, "max_parallel", int)
        sched = self._scheduler_view(now)
        records = observe._running_ledger(org)
        inflight = [a for a in agents if org.running(a)]
        free = max_parallel - len(inflight)
        sched_up = sched.state == "running"
        rows: dict[str, AgentRow] = {}
        root_row = AgentRow(ROOT, ROOT, 0, None, "you (the human, root of the organization)", "", "you", GLYPHS["you"], "you",
                            None, unread=org.unread(ROOT), delegated=len(org.outstanding(ROOT)))
        rows[ROOT] = root_row
        for a in agents:
            rows[a] = self._agent_row(a, now, records, sched_up, free, max_parallel)
        for a in agents:  # children lists from the addresses (one listing, no second directory walk)
            parent = org.parent(a) or ROOT
            if parent in rows and a not in rows[parent].children:
                rows[parent].children.append(a)
        for a in reversed(agents):  # roll running / queued up to the ancestors (shown when a node is collapsed)
            r = rows[a]
            p = rows.get(r.parent or ROOT)
            if p is not None and p.addr != a:
                p.below_running += r.below_running + (r.kind == "running")
                p.below_queued += r.below_queued + (r.kind == "queued")
        order = [ROOT]
        stack = list(reversed(rows[ROOT].children))
        while stack:
            a = stack.pop()
            if a in rows:
                order.append(a)
                stack.extend(reversed(rows[a].children))
        needs = prog._human_items(org)
        retired = 0
        try:
            retired = sum(1 for p in (org.root / ".retired").iterdir() if p.is_dir())
        except OSError:
            pass
        sig = self._signature(agents)
        snap = Snapshot(
            org_name=org.root.name, root=str(org.root), at=now, scheduler=sched, max_parallel=max_parallel, agents=rows,
            order=order, running=len(inflight), queued=sum(1 for a in agents if rows[a].kind == "queued"), needs_you=needs,
            errors_15m=self.feed.error_count(now), last_event=self.feed.last_ts, events_seen=self.feed.any,
            bad_files=org.bad, retired=retired, sig=sig,
        )
        snap.ms = (time.perf_counter() - t0) * 1000
        self.snap = snap
        return snap

    def _signature(self, agents: list[str]) -> tuple:
        org = self.org
        parts: list = [_mtime(org.root / "ORG.md")]
        for a in (ROOT, *agents):
            parts.append(tuple(org.mtime(a, b) for b in (*BOXES, "runs", ".paused")))
        return tuple(parts)

    def _agent_row(self, a: str, now: datetime, records: dict, sched_up: bool, free: int, max_parallel: int) -> AgentRow:
        org = self.org
        meta, _ = org.charter(a)
        role = str(meta.get("role") or "?")
        model = str(meta.get("model") or "").strip() or org.default_model
        running = org.running(a)
        unread = org.unread(a)
        paused = org.paused(a)
        budget = org.budget(a) or 0
        open_n = len(org.open_tasks(a))
        out_n = len(org.outstanding(a))
        elapsed = self._elapsed(a, records.get(a), now) if running else None
        st = classify(running=running, unread=unread, paused=paused, budget=budget, open_tasks=open_n, delegated=out_n,
                      scheduler_up=sched_up, free_slots=free, max_parallel=max_parallel, elapsed_s=elapsed)
        kind, word, reason = st.kind, st.word, st.reason
        behind = unread if running else 0
        return AgentRow(
            addr=a, name=a.rsplit("/", 1)[-1], depth=org.depth(a), parent=org.parent(a), role=role, model=model, kind=kind,
            glyph=GLYPHS[kind], word=word, budget=budget, unread=unread, open_tasks=open_n, delegated=out_n,
            runs_used=org.runs_used(a), paused=paused, elapsed_s=elapsed, reason=reason, queued_behind=behind,
            services=org.service_names(a), main=st.main, note=st.note, short=st.short,
        )

    def _elapsed(self, a: str, rec: dict | None, now: datetime) -> float | None:
        rec = rec or {}
        started = rec.get("started")
        if isinstance(started, (int, float)) and not isinstance(started, bool):
            t0 = datetime.fromtimestamp(started, timezone.utc)
        else:
            stem = Path(str(rec.get("log", ""))).stem if rec.get("log") else None
            if stem is None:
                logs = observe._run_logs(self.org, a)
                stem = logs[-1][0] if logs else None
            t0 = _stamp(stem) if stem else None
        return max(0.0, (now - t0).total_seconds()) if t0 else None

    # ---------------------------------------------------------------------------------------- readable events
    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        """(type, title, sender) of a message in the mailbox of ``agent`` (inbox, in flight or read), for the batch of a
        'run started' line. One dict per mailbox listing, rebuilt only when the listing changed."""
        try:
            merged = self.org.messages(agent, "inbox", "inflight", "read")
        except Exception:  # noqa: BLE001
            return None
        hit = self._msg_index.get(agent)
        if hit is None or hit[0] is not merged:
            hit = (merged, {m.id: m for m in merged})
            self._msg_index[agent] = hit
            if len(self._msg_index) > 200:
                self._msg_index.pop(next(iter(self._msg_index)))
        m = hit[1].get(mid)
        return (m.type, m.title, m.sender) if m is not None else None

    def event_lines(self, events: list[dict], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        return event_lines(events, me=me, actor=actor, raw=raw, lookup=self.message_lookup)

    # ---------------------------------------------------------------------------------------- scheduler
    def _scheduler_view(self, now: datetime) -> SchedulerView:
        org = self.org
        t = time.monotonic()
        if self._sched is None or t - self._sched[0] > self.scheduler_ttl:
            try:
                st = scheduler_state(org)
            except Exception:  # noqa: BLE001
                st = SchedulerState("stopped")
            self._sched = (t, st)  # type: ignore[assignment]
        st = self._sched[1]  # type: ignore[assignment]
        view = SchedulerView(st.state, st.pid, st.since, detail=st.detail)
        try:
            files = observe._scheduler_files(org)
        except Exception:  # noqa: BLE001
            files = []
        if st.state == "running" and st.pid is not None:
            mine = [f for f in files if f[1] == st.pid]
            if mine:
                facts = self._file_facts(mine[0][2])
                view.mode = facts.get("mode")
                if facts.get("start"):
                    view.uptime_s = (now - facts["start"]).total_seconds()
                beat = self._feed_heartbeat(st.pid) or facts.get("beat")
                if beat:
                    view.heartbeat_age_s = max(0.0, (now - beat).total_seconds())
        else:
            for _, _, path in files[:3]:
                facts = self._file_facts(path)
                if facts.get("exit"):
                    view.last_exit = facts["exit"]
                    break
            if not view.last_exit:
                try:
                    view.last_exit = (org.root / EXIT_FILE).read_text(encoding="utf-8").strip() or None
                except OSError:
                    pass
        return view

    def _feed_heartbeat(self, pid: int) -> datetime | None:
        if self.feed is None:
            return None
        for ev in reversed(self.feed.events):
            if ev.get("kind") == "scheduler.heartbeat" and ev.get("pid") == pid:
                return observe._ts(ev.get("ts"))
        return None

    def _file_facts(self, path: Path) -> dict:
        """start / mode / last heartbeat / exit reason of one scheduler event file, re-read only when it changed."""
        try:
            st = path.stat()
        except OSError:
            return {}
        key = (st.st_size, st.st_mtime_ns)
        hit = self._sched_files.get(path)
        if hit is not None and hit[0] == key:
            return hit[1]
        tail = observe._tail_events(path)
        head = observe._head_event(path)
        start = head if head and head.get("kind") == "scheduler.start" else next(
            (e for e in tail if e.get("kind") == "scheduler.start"), None)
        beats = [e for e in tail if e.get("kind") == "scheduler.heartbeat"]
        exits = [e for e in tail if e.get("kind") == "scheduler.exit"]
        facts = {
            "mode": start.get("mode") if start else None,
            "start": observe._ts(start.get("ts")) if start else None,
            "beat": observe._ts(beats[-1].get("ts")) if beats else None,
            "exit": observe._clip(exits[-1].get("reason"), 160) if exits else None,
        }
        self._sched_files[path] = (key, facts)
        return facts

    # ---------------------------------------------------------------------------------------- agent detail
    def agent_detail(self, addr: str, snap: Snapshot | None = None, raw: bool = False) -> AgentDetail:
        self.org.tick()
        snap = snap or self.snap or self.snapshot()
        org = self.org
        row = snap.row(addr)
        if row is None:
            return AgentDetail(addr, None, [Section("", [f"{addr}: no such agent (any more)"])], [], RunLog(), "", "", [])
        events = self.feed.matching(agent=addr, limit=300) if self.feed else []
        return AgentDetail(
            addr=addr, row=row, overview=self._overview(addr, row, snap, events), messages=self._messages(addr),
            runlog=self.run_log(addr, row.kind == "running") if addr != ROOT else RunLog(note="root is the human: no runs"),
            memory=self._memory(addr), charter=self._charter(addr), events=events,
            activity=self.event_lines(events, me=addr, raw=raw),
        )

    def _overview(self, addr: str, row: AgentRow, snap: Snapshot, events: list[dict]) -> list[Section]:
        org = self.org
        if addr == ROOT:
            return self._root_overview(snap)
        doc: list[Section] = []
        meta, _ = org.charter(addr)
        head = [f"state    {row.glyph} {row.word}", f"role     {row.role}", f"model    {row.model}",
                f"budget   {row.budget} run(s) left; {row.runs_used} run(s) used",
                f"mailbox  {row.unread} unread, {row.open_tasks} open task(s), {row.delegated} delegated and outstanding"]
        if row.parent:
            head.insert(1, f"parent   {row.parent}")
        if row.services:
            head.append("offers   " + ", ".join(row.services))
        if meta.get("tools"):
            head.append("tools    " + ", ".join(map(str, meta["tools"])))
        if meta.get("workspace"):
            head.append(f"workspace {meta['workspace']}")
        doc.append(Section(addr, head))
        if row.kind == "running":
            doc.append(Section("Current run", self._current_run(addr, row)))
        elif row.kind == "queued":
            doc.append(Section("Queued", [f"{row.unread} unread message(s) wait: {row.reason}"]))
        elif row.kind == "paused":
            doc.append(Section("Paused", [row.main, *([f"{row.unread} unread message(s) wait; nothing starts until it is resumed"]
                                                       if row.unread else [])]))
        elif row.kind == "budget":
            doc.append(Section("Out of budget", [
                "no runs left" + (f"; {row.unread} unread message(s) wait until budget is granted" if row.unread
                                  else "; it has work but cannot run until budget is granted")]))
        tasks = org.open_tasks(addr)
        doc.append(Section(f"Open tasks ({len(tasks)})", self._task_lines(tasks) or ["none"]))
        out = org.outstanding(addr)
        lines = []
        for t in out:
            target = snap.row(t.to)
            lines.append(f'"{t.title}" -> {t.to}  [{target.word if target else "gone"}]  budget {t.budget}')
        doc.append(Section(f"Delegated, outstanding ({len(out)})", lines or ["none"]))
        recent = event_lines(events[-8:], me=addr, lookup=self.message_lookup)
        doc.append(Section("Latest activity", [x.text for x in recent] or ["(no events for this agent)"],
                           frozenset(i for i, x in enumerate(recent) if x.error)))
        return doc

    def _task_lines(self, tasks: list[Message]) -> list[str]:
        lines: list[str] = []
        for t in tasks:
            lines.append(f'"{t.title}"  from {t.sender}  budget {t.budget}')
            crit = prog._section(t.body, "acceptance criteria")
            for c in crit[:6]:
                lines.append(f"    · {observe._clip(c.lstrip('-* '), 110)}")
            if len(crit) > 6:
                lines.append(f"    · … {len(crit) - 6} more")
        return lines

    def _current_run(self, addr: str, row: AgentRow) -> list[str]:
        org = self.org
        batch = org.messages(addr, "inflight")
        lines = [f"elapsed {fmt_dur((row.elapsed_s or 0) * 1000)}"]
        lines.append(f"batch of {len(batch)} message(s):")
        for m in batch:
            lines.append(f'  {m.type} "{m.title or m.id}" from {m.sender}' + (f"  [{m.status}]" if m.status else ""))
        if row.queued_behind:
            lines.append(f"{row.queued_behind} more message(s) wait for the next run")
        return lines

    def _root_overview(self, snap: Snapshot) -> list[Section]:
        org = self.org
        doc = [Section("You (root)", [f"{len(snap.agents) - 1} agent(s); {snap.running} running, {snap.queued} queued"
                                       + (f"; {snap.retired} retired" if snap.retired else ""),
                                       snap.scheduler.text])]
        doc.append(Section(f"Needs you ({len(snap.needs_you)})", [line for _, line in snap.needs_you] or ["nothing"]))
        reqs = self.requests(snap)
        lines = []
        for r in reqs:
            if r.klass in ("done", "failed") and r.last_activity_s is not None and r.last_activity_s > 86400:
                continue
            lines.append(f'"{r.title}" -> {r.assignee}: {r.state}' + (f" ({r.who})" if r.who else "") + f". {r.runs_text}"
                         + (f". last activity {fmt_dur(r.last_activity_s * 1000)} ago" if r.last_activity_s is not None else ""))
        doc.append(Section("Requests", lines[:30] or ["no requests yet"]))
        if snap.bad_files:
            doc.append(Section("Unreadable files", [f"{p}: {why}" for p, why in list(snap.bad_files.items())[:10]]))
        return doc

    def _messages(self, addr: str, limit: int = 300) -> list[MsgRow]:
        org = self.org
        rows: list[MsgRow] = []
        for box in BOXES:
            for m in org.messages(addr, box):
                rows.append(MsgRow(m.id, box, m.type, m.sender, m.to, m.title, m.status, m.budget, _stamp(m.id), m.path))
        rows.sort(key=lambda r: (r.id, r.box))
        return rows[-limit:][::-1]  # newest first

    def message_text(self, row: MsgRow) -> str:
        """The message as ``Message.render`` shows it, whole (capped), or why it cannot be read."""
        try:
            m = Message.load(row.path) if row.path else None
        except Exception as exc:  # noqa: BLE001
            return f"cannot read {row.path}: {type(exc).__name__}: {exc}"
        if m is None:
            return "(message file is gone)"
        body = m.render(limit=0)
        return clean_text(body[:TEXT_CAP] + (f"\n[... {len(body) - TEXT_CAP} more characters in {row.path}]" if len(body) > TEXT_CAP else ""))

    def _read_cached(self, path: Path, cap: int = TEXT_CAP) -> str:
        try:
            st = path.stat()
        except OSError:
            return ""
        key = (st.st_mtime_ns, st.st_size)
        hit = self._texts.get(path)
        if hit and hit[0] == key:
            return hit[1]
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        text = clean_text(text)
        if len(text) > cap:
            text = f"[... {len(text) - cap} earlier characters not shown]\n" + text[-cap:]
        self._texts[path] = (key, text)
        return text

    def _memory(self, addr: str) -> str:
        return self._read_cached(self.org.dir(addr) / "MEMORY.md") or "(no memory yet)"

    def _charter(self, addr: str) -> str:
        if addr == ROOT:
            return "root is the human: no charter.\n\nORG.md rules:\n\n" + self._read_cached(self.org.root / "ORG.md")
        return self._read_cached(self.org.dir(addr) / "AGENT.md") or "(no charter)"

    # ---------------------------------------------------------------------------------------- run log
    def run_log(self, addr: str, live: bool) -> RunLog:
        """The tail of the agent's current run log (running) or latest run log. Reads at most the last ~1 MB, only when
        the file changed since the last call."""
        org = self.org
        path: Path | None = None
        if live:
            rec = observe._running_ledger(org).get(addr) or {}
            if rec.get("log"):
                cand = org.root / str(rec["log"])
                if cand.is_file() and org.root in cand.resolve().parents:
                    path = cand
        if path is None:
            logs = observe._run_logs(org, addr)
            path = logs[-1][1] if logs else None
        if path is None:
            return RunLog(note="this agent has not run yet")
        try:
            st = path.stat()
        except OSError:
            return RunLog(note="the run log is gone")
        key = (st.st_size, st.st_mtime_ns, live)
        hit = self._logs.get(path)
        if hit is not None and hit[0] == key:
            return hit[1]
        log = _read_tail(path, org._rel(path), live)
        self._logs[path] = (key, log)
        if len(self._logs) > 40:
            self._logs.pop(next(iter(self._logs)))
        return log

    # ---------------------------------------------------------------------------------------- requests
    def requests(self, snap: Snapshot | None = None) -> list[RequestRow]:
        self.org.tick()
        snap = snap or self.snap or self.snapshot()
        return self._memoised("requests", snap.sig + (len(snap.needs_you),), REQUESTS_TTL, lambda: self._requests(snap))  # type: ignore[return-value]

    def _requests(self, snap: Snapshot) -> list[RequestRow]:
        org, now = self.org, snap.at
        tasks = [m for m in org.sent(ROOT) if m.type == "task"]
        results = latest_results(org.received(ROOT))
        waiting: dict[str, int] = {}
        for mid, _ in snap.needs_you:
            tr = org.trace_of(ROOT, mid)
            if tr:
                waiting[tr] = waiting.get(tr, 0) + 1
        rows: list[RequestRow] = []
        for t in reversed(tasks[-300:]):
            res = results.get(t.id)
            try:
                team = [a for a in org.subtree(t.to) if a != ROOT] if org.exists(t.to) else []
                state, who = prog._state(org, t, res, team)
                runs_text = prog._runs(org, t, res, team)
                last = prog._last_activity(org, team)
            except Exception as exc:  # noqa: BLE001 - one odd request must not hide the others
                state, who, runs_text, last = f"? ({type(exc).__name__})", "", "runs ?", None
            m = re.match(r"runs (\d+) of (\d+)", runs_text)
            arts = prog._artifacts(res) if res is not None and res.status in ("done", "failed") else []
            rows.append(RequestRow(
                id=t.id, title=t.title, assignee=t.to, service=t.service, revises=t.revises, state=state,
                klass=re.split(r"[ :(]", state, 1)[0], who=who, runs_used=int(m.group(1)) if m else 0,
                runs_given=int(m.group(2)) if m else 0, runs_text=runs_text,
                last_activity_s=max(0.0, (now - last).total_seconds()) if last else None, created=_stamp(t.id),
                needs_you=waiting.get(t.id, 0), artifacts=arts,
            ))
        return rows

    def request_line(self, task_id: str) -> str:
        """The ``progress`` line of one request."""
        try:
            return prog.progress(self.org, task_id, self.now()).splitlines()[0]
        except Exception as exc:  # noqa: BLE001
            return f"(no progress line: {exc})"

    def trace_text(self, task_id: str) -> str:
        """The trace of one request (``observe.trace`` rendered), or why there is none."""
        try:
            return clean_text(observe.render_trace(observe.trace(self.org, task_id, self.now())))
        except OrgError as exc:
            return f"no trace: {exc}"
        except Exception as exc:  # noqa: BLE001
            return f"the trace could not be computed: {type(exc).__name__}: {exc}"

    # ---------------------------------------------------------------------------------------- services
    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        self.org.tick()
        snap = snap or self.snap or self.snapshot()
        return self._memoised("services", snap.sig, SERVICES_TTL, self._services)  # type: ignore[return-value]

    def _services(self) -> list[ServiceRow]:
        org = self.org
        rows: list[ServiceRow] = []
        for owner in org.agents():
            for name in org.service_names(owner):
                try:
                    c = services.read_contract(org, owner, name)
                    if c is None:
                        continue
                    pb = services.read_playbook(org, owner, name)
                    stats = services.summarize(services.cases(org, owner, name))
                except Exception as exc:  # noqa: BLE001
                    rows.append(ServiceRow(owner, name, 0, 0, False, services.Stats(), f"unreadable: {type(exc).__name__}", ""))
                    continue
                rows.append(ServiceRow(owner, name, c.version, pb.version, c.locked, stats, pb.reason, c.description))
        return rows

    def service_detail(self, owner: str, name: str) -> list[Section]:
        org = self.org
        try:
            c = services.read_contract(org, owner, name)
            if c is None:
                return [Section("", [f"{owner}/{name}: no such service (retired?)"])]
            pb = services.read_playbook(org, owner, name)
            items = services.cases(org, owner, name)
        except Exception as exc:  # noqa: BLE001
            return [Section("", [f"cannot read the service: {type(exc).__name__}: {exc}"])]
        stats = services.summarize(items)
        doc = [Section(f"{name} (owner {owner})", [
            c.description or "(no description)",
            f"contract v{c.version}" + (" (locked)" if c.locked else "") + f", budget {c.budget} per request"
            + (f", defined by {c.defined_by}" if c.defined_by else ""),
            f"playbook v{pb.version}" + (f" revised by {pb.by or '?'}: {pb.reason}" if pb.version else " (none yet)"),
        ])]
        doc.append(Section("Record", [stats.line()]))
        by_v = services.stats_by_version(items)
        if by_v:
            doc.append(Section("By playbook version", [f"v{v}: {s.line()}" for v, s in by_v.items()]))
        lines = []
        for case in reversed(items):
            bits = [f'{case.id}  "{observe._clip(case.title, 50)}"  {case.state}', f"playbook v{case.used}",
                    f"{case.runs} of {case.budget} runs"]
            if case.reworks:
                bits.append(f"{case.reworks} rework(s)")
            if case.verdicts:
                bits.append("feedback: " + services._verdict_chain(case))
            lines.append(", ".join(bits))
        doc.append(Section(f"Cases ({len(items)})", lines or ["none yet"]))
        doc.append(Section("Contract", [
            "inputs: " + (", ".join(f"{i['name']}{'*' if i['required'] else ''}" for i in c.inputs) or "none"),
            *[f"  accept: {a}" for a in c.acceptance],
            "deliverable: " + ", ".join(f"{k}={v}" for k, v in c.deliverable.items()),
        ]))
        doc.append(Section(f"Playbook v{pb.version}" if pb.version else "Playbook", (pb.body or "(none)").splitlines()))
        return doc

    # ---------------------------------------------------------------------------------------- health
    def health(self, snap: Snapshot | None = None) -> HealthView:
        self.org.tick()
        snap = snap or self.snap or self.snapshot()
        return self._memoised("health", snap.sig, HEALTH_TTL, lambda: self._health(snap))  # type: ignore[return-value]

    def _health(self, snap: Snapshot) -> HealthView:
        org, now = self.org, snap.at
        try:
            now_text = self._now_text(observe.now_view(org, now))
        except Exception as exc:  # noqa: BLE001
            now_text = f"(observe now failed: {type(exc).__name__}: {exc})"
        flagged: list[tuple[str, list[tuple[str, str]]]] = []
        try:
            report = org_health(org, ROOT, now)
            flagged = [(h.addr, list(h.flags.items())) for h in report.flagged]
            summary = f"{len(report.agents)} agent(s), {len(flagged)} flagged"
        except Exception as exc:  # noqa: BLE001
            summary = f"health failed: {type(exc).__name__}: {exc}"
        return HealthView(clean_text(now_text), flagged, summary, now)

    def _now_text(self, v: dict) -> str:
        """``observe.render_now`` with the two things that differ from the rest of the dashboard put right: agents that
        are paused / out of budget are not 'queued' (they are listed apart), and the recent errors are readable lines."""
        queued = v.get("queued") or []
        held = [q for q in queued if str(q["reason"]).startswith("paused") or q["reason"] == "no budget"]
        errs = (v.get("errors_15m") or {}).get("events") or []
        v2 = {**v, "queued": [q for q in queued if q not in held],
              "errors_15m": {**(v.get("errors_15m") or {}), "events": []}}
        lines = observe.render_now(v2).split("\n")
        if held:
            at = next((i for i, ln in enumerate(lines) if ln.startswith("waiting on you")), len(lines))
            extra = [f"not started, with unread mail ({len(held)}):"]
            for q in held:
                why = pause_text(q["reason"].removeprefix("paused: ")) if q["reason"].startswith("paused") else "out of budget"
                age = f", oldest {fmt_dur(q['waiting_s'] * 1000)}" if q.get("waiting_s") is not None else ""
                extra.append(f"  {q['agent']}: {q['unread']} unread{age} - {why}")
            lines[at:at] = extra
        if errs:
            at = next((i for i, ln in enumerate(lines) if ln.startswith("errors in the last 15 min")), None)
            if at is not None:
                lines[at + 1:at + 1] = ["  " + x.text for x in self.event_lines(errs, actor=True)]
        return "\n".join(lines)

    def run_check(self) -> tuple[datetime, str, bool]:
        """``observe.check`` (on demand): (when, rendered text, all passed)."""
        now = self.now()
        try:
            res = observe.check(self.org, now)
            self.check_result = (now, observe.render_check(res), bool(res["ok"]))
        except Exception as exc:  # noqa: BLE001
            self.check_result = (now, f"the check could not run: {type(exc).__name__}: {exc}", False)
        return self.check_result


def _read_tail(path: Path, rel: str, live: bool) -> RunLog:
    log = RunLog(path=path, rel=rel, running=live)
    try:
        with open(path, "rb") as f:
            size = f.seek(0, 2)
            log.size = size
            f.seek(max(0, size - LOG_BYTES))
            data = f.read()
            head_raw = b""
            if size > len(data):
                f.seek(0)
                head_raw = f.read(4096)
    except OSError:
        log.note = "the run log could not be read"
        return log
    text = data.decode("utf-8", errors="replace")
    cut = size > len(data)
    if cut and "\n" in text:
        text = text.split("\n", 1)[1]  # the first line is cut
    lines = clean_text(text).split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # no trailing empty line (a partial last line is kept as it is)
    if len(lines) > LOG_LINES:
        lines = lines[-LOG_LINES:]
        cut = True
    log.truncated = cut
    log.lines = lines
    head_text = clean_text((head_raw or data[:4096]).decode("utf-8", errors="replace"))
    stem_time = _stamp(path.stem)
    header = [f"started {stem_time:%Y-%m-%d %H:%M:%S}Z" if stem_time else f"log {path.name}"]
    for ln in head_text.split("\n")[:8]:
        if ln.startswith(("# run of", "# senders:")):
            header.append(ln[2:])
    tail = "\n".join(lines[-40:])
    ends = re.findall(r"^# (exit -?\d+ after \d+s|failed to start.*|killed after.*|interrupted by scheduler shutdown.*|killed:.*)$",
                      tail, re.M)
    header.append(ends[-1] if ends else ("still running" if live else "no exit line (still running or interrupted)"))
    log.header = header
    return log


# ================================================================================================ plain-text snapshot


def render_once(data: DashData, width: int = 110) -> str:
    """The ``orgmcp dash --once`` output: header, the agent tree with states, requests, services."""
    snap = data.snapshot()
    out = [f"orgmcp dash - {snap.org_name} ({snap.root})  {snap.at:%Y-%m-%d %H:%M:%S}Z",
           f"{snap.scheduler.text} | {snap.counts_text}", ""]
    out.append("AGENTS")
    for addr in snap.order:
        r = snap.agents[addr]
        indent = "  " * r.depth
        if addr == ROOT:
            out.append(f"{r.glyph} root (you)" + (f"  needs you: {len(snap.needs_you)}" if snap.needs_you else ""))
            continue
        budget = "" if r.budget is None else f"  budget {r.budget}"
        out.append(f"{indent}{r.glyph} {r.name} [{r.role}]  {r.word}{budget}  {r.model}")
    if snap.needs_you:
        out += ["", "NEEDS YOU"] + [f"  {line}" for _, line in snap.needs_you]
    out += ["", "REQUESTS"]
    reqs = data.requests(snap)
    if reqs:
        for r in reqs[:20]:
            last = f", last activity {fmt_dur(r.last_activity_s * 1000)} ago" if r.last_activity_s is not None else ""
            out.append(f'  "{observe._clip(r.title, 40)}" -> {r.assignee}: {r.state}{" (" + r.who + ")" if r.who else ""}; {r.runs_text}{last}')
    else:
        out.append("  none")
    out += ["", "SERVICES"]
    svc = data.services(snap)
    if svc:
        for s in svc:
            out.append(f"  {s.owner}/{s.name}  contract v{s.contract_version} playbook v{s.playbook_version}  {s.stats.line()}")
    else:
        out.append("  none")
    if snap.bad_files:
        out += ["", f"UNREADABLE FILES ({len(snap.bad_files)})"] + [f"  {p}: {w}" for p, w in list(snap.bad_files.items())[:5]]
    return "\n".join(out)  # whole lines: this output is read by people and scripts, never cut
