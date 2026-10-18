"""Observability, the query half: read-only views over the event log, the message files and the run logs.

Everything here is a pure function of the files in an organization directory (nothing is written, no lock is taken):

* ``now``     what is happening right now: scheduler, runs in flight, what is queued and why, what waits on you,
              what broke in the last 15 minutes;
* ``trace``   one request (a root task) as a tree: messages, runs, tool calls and refusals, with totals;
* ``metrics`` counts, rates and latency percentiles over a time window, optionally grouped;
* ``events``  the merged raw stream of the per-process event files (filterable, followable);
* ``check``   invariants of the runtime itself (messages intact, budget conserved, nothing stuck, runs accounted for).

Each view returns a JSON-able dict; ``render_*`` turn it into compact text. ``observe_text`` is the single entry point
used by the MCP tool ``observe`` and by the CLI.

The event files are written by the runtime (see the observability spec, section 2): one append-only JSONL file per
process per UTC day, ``.runtime/events/<YYYY-MM-DD>/<proc>-<pid>-<start_epoch_ms>.jsonl``. The readers tolerate what
a live system produces: a partial last line, unknown kinds and fields, missing directories, files of other days, and
an organization that has no events at all (then ``trace`` falls back to the message files and run logs and says so).
"""

from __future__ import annotations

import heapq
import json
import math
import os
import re
import time
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator

from .core import BOXES, ROOT, RUNTIME, Org, OrgError, split_frontmatter, utcnow
from .health import _aware, _stamp, config_number
from .review import retired_runs
from .runs import RunLogReader
from .scheduler import EXIT_FILE, judge_orphan, scheduler_state

EVENTS_DIR = Path(".runtime") / "events"
ERROR_WINDOW = timedelta(minutes=15)
COPY_GRACE = 5.0  # seconds a freshly written message may lack its other copy (delivery writes two files)
INFLIGHT_GRACE = 30.0  # seconds an inflight batch may exist before the run record is written
RECV_BOXES = ("inbox", "inflight", "read")
ENVELOPE = {"v", "ts", "seq", "proc", "pid", "kind", "actor", "run", "trace"}
READ_ONLY_TOOLS = {"inbox", "read", "status", "health", "progress", "whoami", "services", "observe", "org_read"}
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
VIEWS = ("now", "trace", "metrics", "events", "check")


# ============================================================================================ small helpers


def fmt_dur(ms: float | None) -> str:
    """A duration: ``850ms``, ``4.2s``, ``42s``, ``1m05s``, ``2h03m``."""
    if ms is None:
        return "?"
    ms = max(0.0, float(ms))
    if ms == 0:
        return "0s"
    if ms < 1000:
        return f"{ms:.0f}ms"
    s = ms / 1000
    if s < 10:
        return f"{s:.1f}s"
    s = int(round(s))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def fmt_rel(ms: float) -> str:
    """Time relative to the start of a request: ``+0s``, ``+42s``, ``+1m05s``, ``+2h03m``."""
    s = int(max(0.0, ms) // 1000)
    if s < 60:
        return f"+{s}s"
    if s < 3600:
        return f"+{s // 60}m{s % 60:02d}s"
    return f"+{s // 3600}h{(s % 3600) // 60:02d}m"


def _clip(text: object, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _iso(t: datetime | None) -> str | None:
    return t.astimezone(timezone.utc).isoformat() if t else None


def _ms(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() * 1000


def _plain(value):
    """JSON-able copy: datetimes as ISO strings, tuples/sets as lists, Paths as strings."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Path):
        return str(value)
    return value


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile: the ``ceil(p/100 * n)``-th smallest value (exact, no interpolation); None if empty."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _stats(values: list[float]) -> dict:
    return {"n": len(values), "p50": percentile(values, 50), "p95": percentile(values, 95),
            "max": max(values) if values else None}


_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
_SPAN = re.compile(r"(\d+(?:\.\d+)?)\s*([smhdw])")


def parse_when(text: str | datetime | None, now: datetime | None = None) -> datetime | None:
    """A point in time from ``15m`` / ``24h`` / ``7d`` (that long before ``now``), ``now``, or an ISO timestamp
    (a naive one is UTC). None for None or an empty string."""
    if text is None or text == "":
        return None
    if isinstance(text, datetime):
        return _aware(text)
    now = _aware(now) or utcnow()
    raw = str(text).strip()
    m = _SPAN.fullmatch(raw.lower())
    if m:
        return now - timedelta(seconds=float(m.group(1)) * _UNITS[m.group(2)])
    if raw.lower() == "now":
        return now
    try:
        return _aware(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        raise OrgError(f"cannot read {raw!r} as a time: use a duration like 15m, 24h, 7d or an ISO timestamp "
                       "like 2026-10-18T10:00:00Z") from None


def _ts(value) -> datetime | None:
    try:
        return _aware(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def _cap(lines: list[str], max_lines: int | None, hint: str) -> list[str]:
    if max_lines is None or len(lines) <= max_lines:
        return lines
    return lines[:max_lines] + [f"... {len(lines) - max_lines} more line(s), narrow with {hint}"]


# ============================================================================================ the event log


def _day_dirs(org: Org, since: datetime | None, until: datetime | None) -> list[Path]:
    base = org.root / EVENTS_DIR
    try:
        names = sorted(n for n in os.listdir(base) if _DAY.fullmatch(n) and (base / n).is_dir())
    except OSError:
        return []
    lo = since.astimezone(timezone.utc).date().isoformat() if since else None
    hi = until.astimezone(timezone.utc).date().isoformat() if until else None
    return [base / n for n in names if (lo is None or n >= lo) and (hi is None or n <= hi)]


def event_files(org: Org, since: datetime | None = None, until: datetime | None = None) -> list[Path]:
    """The event files that can hold events in ``[since, until]``: day directories first, then files by mtime
    (a file not written since ``since`` has nothing newer)."""
    out = []
    for d in _day_dirs(org, since, until):
        try:
            names = sorted(n for n in os.listdir(d) if n.endswith(".jsonl") and not n.startswith("."))
        except OSError:
            continue
        for n in names:
            p = d / n
            try:
                if since is not None and p.stat().st_mtime < since.timestamp():
                    continue
            except OSError:
                continue
            out.append(p)
    return out


def _read_events(path: Path) -> Iterator[tuple[datetime, dict]]:
    """(time, event) of every parsable line of one file; partial and foreign lines are skipped."""
    try:
        f = open(path, "rb")
    except OSError:
        return
    with f:
        for raw in f:
            try:
                ev = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(ev, dict):
                continue
            t = _ts(ev.get("ts"))
            if t is not None:
                yield t, ev


def timed_events(org: Org, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, dict]]:
    """Events in ``[since, until]`` as (time, event), merged over all process files in time order (a heap merge:
    every file is time-ordered by its single writer)."""
    streams = [_read_events(p) for p in event_files(org, since, until)]
    for t, ev in heapq.merge(*streams, key=lambda item: item[0]):
        if since is not None and t < since:
            continue
        if until is not None and t > until:
            continue
        yield t, ev


def iter_events(org: Org, since: datetime | None = None, until: datetime | None = None) -> Iterator[dict]:
    for _, ev in timed_events(org, since, until):
        yield ev


def is_error(ev: dict) -> bool:
    """Events that mean something went wrong: a refused or failed tool call, a failed command, a run that did not end
    cleanly, a scheduler phase that raised, an orphaned run, an agent failure."""
    kind = ev.get("kind")
    if kind in ("tool.call", "cli.command"):
        return ev.get("ok") is False
    if kind == "run.end":
        return ev.get("ok") is False or bool(ev.get("timed_out") or ev.get("killed"))
    return kind in ("scheduler.error", "run.orphan", "agent.failure")


def _matcher(agent: str | None = None, kind: str | None = None, trace: str | None = None,
             errors: bool = False) -> Callable[[dict], bool]:
    agent = Org.norm(agent) if agent else None
    kind = kind.rstrip("*").rstrip(".") if kind else None

    def match(ev: dict) -> bool:
        if kind:
            k = str(ev.get("kind", ""))
            if k != kind and not k.startswith(kind + "."):
                return False
        if agent and agent not in (ev.get("actor"), ev.get("agent"), ev.get("from"), ev.get("to")):
            return False
        if trace and trace != ev.get("trace") and trace not in (ev.get("traces") or ()):
            return False
        return not errors or is_error(ev)

    return match


def events_view(org: Org, since=None, until=None, agent: str | None = None, kind: str | None = None,
                trace: str | None = None, errors: bool = False, limit: int | None = None,
                now: datetime | None = None) -> dict:
    """The merged raw stream, filtered by time window first, then by fields. With ``limit`` the LAST ``limit`` events
    of the window are kept (``total`` counts all that matched)."""
    now = _aware(now) or utcnow()
    lo, hi = parse_when(since, now), parse_when(until, now)
    match = _matcher(agent, kind, trace, errors)
    keep: list[dict] = []
    total = 0
    for _, ev in timed_events(org, lo, hi):
        if match(ev):
            total += 1
            keep.append(ev)
            if limit and len(keep) > limit * 2:  # bounded memory on big windows
                del keep[: len(keep) - limit]
    if limit and len(keep) > limit:
        keep = keep[-limit:]
    return {"events": keep, "total": total, "shown": len(keep), "since": _iso(lo), "until": _iso(hi)}


def events(org: Org, since=None, until=None, agent=None, kind=None, trace=None, errors=False, limit=None,
           now: datetime | None = None) -> list[dict]:
    """The matching events (the last ``limit`` of them), oldest first."""
    return events_view(org, since, until, agent, kind, trace, errors, limit, now)["events"]


class Follower:
    """Tails the event files: ``poll()`` returns the complete new lines of all files (today's and yesterday's day
    directories) since the last call, in time order. Files that appear later (a new process) are read from the start."""

    def __init__(self, org: Org, match: Callable[[dict], bool] | None = None, now: datetime | None = None):
        self.org, self.match = org, match or (lambda ev: True)
        self.offsets: dict[Path, int] = {}
        self._seen_first = False
        self.poll(emit=False, now=now)
        self._seen_first = True

    def _files(self, now: datetime | None) -> list[Path]:
        now = _aware(now) or utcnow()
        return event_files(self.org, now - timedelta(days=1), now + timedelta(days=1))

    def poll(self, emit: bool = True, now: datetime | None = None) -> list[dict]:
        out: list[tuple[datetime, dict]] = []
        for p in self._files(now):
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if p not in self.offsets:
                self.offsets[p] = size if not self._seen_first else 0
                if not self._seen_first:
                    continue
            if size <= self.offsets[p]:
                continue
            try:
                with open(p, "rb") as f:
                    f.seek(self.offsets[p])
                    data = f.read(size - self.offsets[p])
            except OSError:
                continue
            end = data.rfind(b"\n")
            if end < 0:
                continue  # no complete line yet
            self.offsets[p] += end + 1
            for raw in data[: end + 1].splitlines():
                try:
                    ev = json.loads(raw)
                except ValueError:
                    continue
                t = _ts(ev.get("ts")) if isinstance(ev, dict) else None
                if t is not None and self.match(ev):
                    out.append((t, ev))
        out.sort(key=lambda item: item[0])
        return [ev for _, ev in out] if emit else []


def follow_events(org: Org, agent=None, kind=None, trace=None, errors=False, poll: float = 0.5,
                  sleep: Callable[[float], None] = time.sleep, max_polls: int | None = None) -> Iterator[dict]:
    """Yield new matching events as they are written (polling). Stops after ``max_polls`` polls if given."""
    follower = Follower(org, _matcher(agent, kind, trace, errors))
    n = 0
    while max_polls is None or n < max_polls:
        yield from follower.poll()
        n += 1
        if max_polls is None or n < max_polls:
            sleep(poll)


def format_event(ev: dict, width: int = 300) -> str:
    """One line: time, process, actor, kind, then the interesting fields."""
    t = _ts(ev.get("ts"))
    clock = (t.strftime("%H:%M:%S") + (f".{t.microsecond // 1000:03d}" if t.microsecond else "")) if t else str(ev.get("ts", ""))[:12]
    kind = str(ev.get("kind", "?"))
    parts = [f"{clock} {str(ev.get('proc', '?')):<9} {str(ev.get('actor') or '-'):<14} {kind}"]
    if kind == "tool.call":
        parts.append(f"{ev.get('tool')} {'ok' if ev.get('ok') else 'REFUSED' if ev.get('error_type') in (None, 'OrgError') else 'FAILED'}"
                     f" {fmt_dur(ev.get('ms'))}")
    elif kind == "run.end":
        parts.append(f"{'ok' if ev.get('ok') else 'FAILED'} {fmt_dur(ev.get('duration_ms'))}"
                     + (" timed-out" if ev.get("timed_out") else "") + (" killed" if ev.get("killed") else ""))
    for key, value in ev.items():
        if key in ENVELOPE or key in ("tool", "ms", "duration_ms") or (kind == "tool.call" and key == "ok"):
            continue
        if kind == "run.end" and key in ("ok", "timed_out", "killed"):
            continue
        if value in (None, "", [], {}):
            continue
        if isinstance(value, dict):
            value = ",".join(f"{k}={v}" for k, v in value.items())
        elif isinstance(value, list):
            value = ",".join(str(v) for v in value)
        parts.append(f"{key}={value}" if key != "error" else f'error="{value}"')
    if ev.get("run"):
        parts.append(f"run={ev['run']}")
    if ev.get("trace"):
        parts.append(f"trace={ev['trace']}")
    return _clip(" ".join(parts), width)


def render_events(view: dict, max_lines: int | None = None) -> str:
    evs = view["events"]
    if not evs:
        return "(no matching events)" + ("" if view.get("any", True) else " - this organization has no event files yet")
    lines = [format_event(ev) for ev in evs]
    head = f"{view['shown']} of {view['total']} matching event(s), oldest first"
    if view["total"] > view["shown"]:
        head += f" - {view['total'] - view['shown']} earlier one(s) not shown: narrow with since/agent/kind/trace or raise the limit"
    return "\n".join([head, *_cap(lines, max_lines, "since/agent/kind/trace")])


# ============================================================================================ message files


@dataclass
class FileRec:
    path: Path
    owner: str
    box: str
    meta: dict | None
    error: str | None
    id: str
    mtime: float


_META_CACHE: dict[tuple, tuple[dict | None, str | None]] = {}
_META_MAX = 50_000


def _read_meta(path: Path) -> tuple[dict | None, str | None, float]:
    try:
        st = path.stat()
        key = (str(path), st.st_mtime_ns, st.st_size)
        hit = _META_CACHE.get(key)
        if hit is not None:
            return hit[0], hit[1], st.st_mtime
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"unreadable ({type(exc).__name__})", 0.0
    try:
        meta, _ = split_frontmatter(text)
    except Exception as exc:  # noqa: BLE001 - yaml errors of any kind
        meta, error = None, f"frontmatter does not parse ({type(exc).__name__})"
    else:
        error = None
        if not meta:
            error = "no frontmatter"
        elif not all(meta.get(k) for k in ("from", "to", "type")):
            error = "frontmatter lacks from/to/type"
        else:
            try:
                int(meta.get("budget") or 0)
            except (TypeError, ValueError):
                error = f"budget is not a number: {meta.get('budget')!r}"
    if len(_META_CACHE) > _META_MAX:
        _META_CACHE.clear()
    _META_CACHE[key] = (meta, error)
    return meta, error, st.st_mtime


def scan_messages(org: Org) -> list[FileRec]:
    """Every message file of every mailbox of root and the live agents, parsed once (cached by path + mtime)."""
    out: list[FileRec] = []
    for owner in (ROOT, *org.agents()):
        for box in BOXES:
            d = org.dir(owner) / box
            try:
                names = sorted(n for n in os.listdir(d) if n.endswith(".md") and not n.startswith("."))
            except OSError:
                continue
            for n in names:
                p = d / n
                meta, error, mtime = _read_meta(p)
                mid = str((meta or {}).get("id") or p.stem)
                out.append(FileRec(p, owner, box, meta, error, mid, mtime))
    return out


@dataclass
class Msg:
    id: str
    sender: str
    to: str
    type: str
    title: str
    status: str | None
    budget: int
    reply_to: str | None
    revises: str | None
    service: str | None
    feedback: str | None
    wake: bool
    trace: str | None  # as recorded in the frontmatter
    t: datetime
    boxes: list[tuple[str, str]] = field(default_factory=list)  # (owner, box) of every copy


def _msg_time(mid: str, meta: dict) -> datetime:
    return _stamp(mid) or _ts(meta.get("created")) or _EPOCH


def build_messages(files: list[FileRec]) -> dict[str, Msg]:
    out: dict[str, Msg] = {}
    for f in files:
        meta = f.meta
        if not meta or f.error:
            continue
        m = out.get(f.id)
        if m is None:
            try:
                budget = int(meta.get("budget") or 0)
            except (TypeError, ValueError):
                budget = 0
            m = out[f.id] = Msg(
                id=f.id, sender=str(meta["from"]), to=str(meta["to"]), type=str(meta["type"]),
                title=str(meta.get("title") or ""), status=meta.get("status"), budget=budget,
                reply_to=str(meta["reply_to"]) if meta.get("reply_to") else None,
                revises=str(meta["revises"]) if meta.get("revises") else None,
                service=str(meta["service"]) if meta.get("service") else None,
                feedback=str(meta["feedback"]) if meta.get("feedback") else None,
                wake=meta.get("wake", True) is not False,
                trace=str(meta["trace"]) if meta.get("trace") else None,
                t=_msg_time(f.id, meta),
            )
        elif not m.trace and meta.get("trace"):
            m.trace = str(meta["trace"])
        m.boxes.append((f.owner, f.box))
    return out


class Traces:
    """The trace of every message: as recorded in its frontmatter (``trace``), else derived from the files with the
    same rules the runtime applies at send time (spec section 3), best effort:

    1. root sends a task without ``revises``: its own id (``new``);
    2. ``reply_to`` / ``revises``: the trace of that message (``link``);
    3. the sender's open tasks at that moment (received, no final result yet) all share one trace (``open-task``);
    4. the sender's batch of that run (from ``run.start`` events, else the messages that arrived between its
       previous run and this one) has exactly one distinct trace (``batch``);
    5. otherwise unknown.
    """

    def __init__(self, org: Org, msgs: dict[str, Msg], batches: dict[str, list[str]] | None = None):
        self.org, self.msgs, self.batches = org, msgs, batches or {}
        self._memo: dict[str, tuple[str | None, str]] = {}
        self._received: dict[str, list[Msg]] = defaultdict(list)
        self._final: dict[tuple[str, str], str] = {}  # (reporter, task id) -> id of its first final result
        for m in sorted(msgs.values(), key=lambda x: x.id):
            self._received[m.to].append(m)
            if m.type == "result" and m.reply_to and m.status in ("done", "failed"):
                self._final.setdefault((m.sender, m.reply_to), m.id)
        self._starts: dict[str, list[tuple[datetime, str]]] = {}

    def of(self, mid: str) -> tuple[str | None, str]:
        """(trace id or None, source) with source ``recorded``, ``derived:<rule>`` or ``unknown``."""
        hit = self._memo.get(mid)
        if hit is not None:
            return hit
        self._memo[mid] = (None, "unknown")  # recursion guard
        m = self.msgs.get(mid)
        res = self._derive(m) if m is not None else (None, "unknown")
        self._memo[mid] = res
        return res

    def _derive(self, m: Msg) -> tuple[str | None, str]:
        if m.trace:
            return m.trace, "recorded"
        if m.sender == ROOT and m.type == "task" and not m.revises:
            return m.id, "derived:new"
        for link in (m.reply_to, m.revises):
            if link and link in self.msgs:
                t = self.of(link)[0]
                if t:
                    return t, "derived:link"
        open_traces = {
            self.of(t.id)[0] for t in self._received.get(m.sender, ())
            if t.type == "task" and t.id < m.id and self._final.get((m.sender, t.id), "~") > m.id
        }
        if len(open_traces) == 1 and None not in open_traces:
            return next(iter(open_traces)), "derived:open-task"
        batch = self._batch_traces(m)
        if len(batch) == 1:
            return next(iter(batch)), "derived:batch"
        return None, "unknown"

    def _run_starts(self, agent: str) -> list[tuple[datetime, str]]:
        if agent not in self._starts:
            d = self.org.dir(agent) / "runs"
            try:
                names = sorted(n for n in os.listdir(d) if n.endswith(".log") and not n.startswith("."))
            except OSError:
                names = []
            self._starts[agent] = [(t, f"{agent}@{n[:-4]}") for n in names if (t := _stamp(n))]
        return self._starts[agent]

    def _batch_traces(self, m: Msg) -> set[str]:
        if m.sender in (ROOT, RUNTIME):
            return set()
        starts = self._run_starts(m.sender)
        i = bisect_right([t for t, _ in starts], m.t) - 1
        if i < 0:
            return set()
        start, rid = starts[i]
        batch = self.batches.get(rid)
        if batch is None:
            lo = starts[i - 1][0] if i > 0 else _EPOCH
            batch = [x.id for x in self._received.get(m.sender, ()) if lo < x.t < start]
        found = {self.of(b)[0] for b in batch if b != m.id and b in self.msgs}
        found.discard(None)
        return found  # type: ignore[return-value]


# ============================================================================================ runs


def _running_ledger(org: Org) -> dict[str, dict]:
    return org.runtime.run_registry.all()


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

    def to_dict(self) -> dict:
        return _plain({k: v for k, v in self.__dict__.items() if k != "log"})


def run_events(evs) -> dict[str, dict[str, dict]]:
    """run id -> {"start": run.start, "end": run.end, "orphan": run.orphan} from an iterable of events or (t, event)."""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for item in evs:
        ev = item[1] if isinstance(item, tuple) else item
        kind = ev.get("kind")
        if kind in ("run.start", "run.end", "run.orphan") and ev.get("run"):
            out[str(ev["run"])][kind.split(".")[1]] = ev
    return out


def _queue_ms(start: datetime, batch: list[str] | None) -> float | None:
    stamps = [t for b in batch or () if (t := _stamp(str(b)))]
    return max(0.0, _ms(min(stamps), start)) if stamps else None


def _make_run(reader: RunLogReader, agent: str, log: Path | None, stem: str, start: datetime, ev: dict[str, dict],
              running_stem: str | None, is_live: bool) -> RunRec:
    run = RunRec(agent=agent, run=f"{agent}@{stem}", start=start, log=log)
    s, e, o = ev.get("start"), ev.get("end"), ev.get("orphan")
    if s:
        run.source = "events"
        run.batch = [str(b) for b in s.get("batch") or []]
        run.traces = [str(t) for t in s.get("traces") or []]
        # the envelope ``pid`` is the EMITTER's (the scheduler); the kiro process is ``child_pid`` (its group: ``pgid``)
        child = s.get("child_pid") if isinstance(s.get("child_pid"), int) else s.get("pgid")
        run.pid = child if isinstance(child, int) and not isinstance(child, bool) else None
        st = _ts(s.get("ts"))
        run.queue_ms = _queue_ms(st or start, run.batch)
    if e:
        run.source = "events"
        run.ok = bool(e.get("ok"))
        run.exit_code = e.get("exit_code") if isinstance(e.get("exit_code"), int) else None
        run.duration_ms = float(e["duration_ms"]) if isinstance(e.get("duration_ms"), (int, float)) else None
        run.error = _clip(e["error"], 500) if e.get("error") else None
        run.end = _ts(e.get("ts"))
        run.outcome = ("timeout" if e.get("timed_out") else "killed" if e.get("killed")
                       else "ok" if run.ok else "failed")
    elif o:
        run.outcome, run.ok = "killed", False
        run.error = _clip(f"orphan: {o.get('action')} {o.get('detail') or ''}", 200)
    elif log is not None:
        facts = reader.facts(log)
        if facts.get("timed_out"):
            run.outcome, run.ok = "timeout", False
        elif facts.get("killed"):
            run.outcome, run.ok = "killed", False
        elif facts.get("failed_start"):
            run.outcome, run.ok = "failed", False
        elif "exit_code" in facts:
            run.exit_code = facts["exit_code"]
            run.ok = facts["exit_code"] == 0
            run.outcome = "ok" if run.ok else "failed"
        if "seconds" in facts:
            run.duration_ms = facts["seconds"] * 1000.0
        if run.outcome == "unknown" and is_live and running_stem == stem:
            run.outcome = "running"
    if run.outcome == "unknown" and is_live and running_stem == stem:
        run.outcome = "running"
    return run


def _run_logs(org: Org, agent: str) -> list[tuple[str, Path]]:
    return [(f.stem, f.path) for f in org.runtime.run_log_reader.files(agent)]


def collect_runs(org: Org, since: datetime | None, until: datetime | None, evs: dict[str, dict[str, dict]] | None = None,
                 agents: list[str] | None = None) -> list[RunRec]:
    """Every run that STARTED in ``[since, until]``: the run logs of the live agents (the file truth: one log = one
    run = one run of budget), completed with ``run.start/run.end`` events where there are some, plus runs known only
    from events (agents retired since). Oldest first."""
    evs = evs if evs is not None else run_events(timed_events(org, since, None))
    running = _running_ledger(org)
    live = {a for a in org.agents() if org.running(a)}
    out: list[RunRec] = []
    seen: set[str] = set()
    for agent in agents if agents is not None else org.agents():
        rec = running.get(agent)
        running_stem = Path(str(rec.get("log", ""))).stem if rec else None
        logs = _run_logs(org, agent)
        for stem, path in logs:
            start = _stamp(stem)
            if start is None or (since and start < since) or (until and start > until):
                continue
            rid = f"{agent}@{stem}"
            seen.add(rid)
            latest = stem == logs[-1][0]
            out.append(_make_run(org.runtime.run_log_reader, agent, path, stem, start, evs.get(rid, {}),
                                 running_stem or (stem if latest else None), agent in live))
    if agents is None:  # runs of agents that no longer exist: only the events know them
        for rid, ev in evs.items():
            s = ev.get("start")
            if rid in seen or not s or "@" not in rid:
                continue
            agent, _, stem = rid.rpartition("@")
            start = _stamp(stem) or _ts(s.get("ts"))
            if start is None or (since and start < since) or (until and start > until) or org.exists(agent):
                continue
            out.append(_make_run(org.runtime.run_log_reader, agent, None, stem, start, ev, None, False))
    return sorted(out, key=lambda r: (r.start, r.run))


# ============================================================================================ trace


def _team(org: Org, task: Msg) -> list[str]:
    return [a for a in org.subtree(task.to) if a != ROOT] if org.exists(task.to) else []


def run_window(org: Org, task: Msg, result: Msg | None, root_tasks: list[Msg]) -> tuple[str, str | None]:
    """(start, end) of a root task's run window, as 21-character timestamps, exactly as ``progress`` counts runs:
    from the task's creation to its final result (``done``/``failed``) or now, cut where root's next task to the same
    assignee begins."""
    start = task.id[:21]
    end = result.id[:21] if result is not None and result.status in ("done", "failed") else None
    later = [t.id[:21] for t in root_tasks if t.to == task.to and t.id > task.id]
    if later and (end is None or later[0] < end):
        end = later[0]
    return start, end


def _in_window(name: str, start: str, end: str | None) -> bool:
    return name[:21] >= start and (end is None or name[:21] <= end)


def _calls_summary(calls: list[dict]) -> dict:
    by_tool = Counter(str(c.get("tool")) for c in calls)
    refused = [{"t": c.get("ts"), "tool": c.get("tool"), "error": _clip(c.get("error") or "", 500),
                "error_type": c.get("error_type"), "actor": c.get("actor")} for c in calls if c.get("ok") is False]
    return {"total": len(calls), "by_tool": dict(by_tool), "refused": refused}


def trace(org: Org, task_id: str, now: datetime | None = None) -> dict:
    """One request as a tree, in time order, with totals. ``task_id`` is a root task id (a message of the request is
    accepted too and resolved to its request). Works from the message files and run logs alone (then ``partial``);
    run/tool-call events add queue wait, durations, tool calls and refusals.

    Totals: ``runs`` is what ``progress`` reports for the task (run logs of the task's team inside the task's window,
    see :func:`run_window`); ``run_ms`` the sum of their durations, ``queue_ms`` the sum of queue waits (run start -
    earliest message of the batch), ``user_wait_ms`` the time items that needed the human (a blocked/failed result or
    a note to root that wakes it) waited for root's next action on the request, ``wall_ms`` task creation to the final
    result (or now).
    """
    now = _aware(now) or utcnow()
    files = scan_messages(org)
    msgs = build_messages(files)
    root_tasks = sorted((m for m in msgs.values() if m.sender == ROOT and m.type == "task"), key=lambda m: m.id)
    if task_id not in msgs:
        known = ", ".join(t.id for t in root_tasks[-5:]) or "none"
        raise OrgError(f"no message {task_id}. Root's tasks (latest): {known}")
    notes: list[str] = []
    redirect = None  # informational only: it does not make the trace partial
    tid = task_id
    is_root_task = task_id in {t.id for t in root_tasks}
    resolved = Traces(org, msgs).of(task_id)[0]
    if not is_root_task and not resolved:
        raise OrgError(f"{task_id} is not a root task and its request cannot be determined. Root's tasks (latest): "
                       + (", ".join(t.id for t in root_tasks[-5:]) or "none"))
    if resolved and resolved != task_id and resolved in msgs:  # a message of the request, or a rework of an earlier task
        redirect = f"{task_id} belongs to the request {resolved}; showing that"
        notes.append(redirect)
        tid = resolved
    evs = list(timed_events(org, msgs[tid].t - timedelta(seconds=2), None))
    batches = {str(ev["run"]): [str(b) for b in ev["batch"]] for _, ev in evs
               if ev.get("kind") == "run.start" and ev.get("run") and isinstance(ev.get("batch"), list)}
    traces = Traces(org, msgs, batches)
    task = msgs[tid]
    # the request = the root task and every rework of it (a rework's `revises` keeps it in the same trace)
    traces_of_root = {t.id: traces.of(t.id)[0] for t in root_tasks}
    chain = [t for t in root_tasks if t.id == tid or (traces_of_root.get(t.id) == tid and t.id > tid)]

    def result_of(t: Msg) -> Msg | None:
        return max((m for m in msgs.values() if m.to == ROOT and m.type == "result" and m.reply_to == t.id),
                   key=lambda m: m.id, default=None)

    steps = [(t, result_of(t)) for t in chain]
    windows = [run_window(org, t, r, root_tasks) for t, r in steps]
    result = steps[-1][1]  # the request's state is its latest task's
    final = result is not None and result.status in ("done", "failed")
    state = result.status if result is not None else "open"
    team = _team(org, task)
    members = set(team)
    start21, end21 = windows[0][0], windows[-1][1]
    t0 = task.t
    t_end = (_stamp(result.id) if final and result is not None else None) or now

    def in_windows(name: str) -> bool:
        return any(_in_window(name, a, b) for a, b in windows)

    # ---- messages of the request
    items: list[dict] = []
    in_trace: dict[str, tuple[Msg, str]] = {}
    for m in msgs.values():
        t, src = traces.of(m.id)
        if t == tid:
            in_trace[m.id] = (m, src)
        elif t is None and m.sender == ROOT and m.to in members and in_windows(m.id):
            in_trace[m.id] = (m, "window")  # root's grants/notes into the team inside the window carry no trace
    for m, src in in_trace.values():
        items.append({"t": m.t, "order": 1, "kind": "message", "agent": m.sender, "id": m.id, "type": m.type,
                      "from": m.sender, "to": m.to, "title": m.title, "status": m.status, "budget": m.budget,
                      "trace_source": src})
    derived = sum(1 for _, s in in_trace.values() if s != "recorded")
    if derived:
        notes.append(f"{derived} message(s) have no recorded trace: their request was derived from reply_to/revises/open "
                     "tasks (marked ~)")

    # ---- runs (file truth) enriched with events
    revs = run_events(evs)
    runs: list[RunRec] = []
    running = _running_ledger(org)
    for agent in team:
        rec = running.get(agent)
        running_stem = Path(str(rec.get("log", ""))).stem if rec else None
        logs = _run_logs(org, agent)
        for stem, path in logs:
            if not in_windows(stem):
                continue
            start = _stamp(stem)
            if start is None:
                continue
            runs.append(_make_run(org.runtime.run_log_reader, agent, path, stem, start, revs.get(f"{agent}@{stem}", {}),
                                  running_stem or (stem if stem == logs[-1][0] else None), org.running(agent)))
    runs.sort(key=lambda r: (r.start, r.run))
    have_events = any(r.source == "events" for r in runs)
    if runs and not have_events:
        notes.append("partial: no run events for this request (queue waits, tool calls and refusals unknown); "
                     "runs and durations come from the run logs")
    elif any(r.source == "log" for r in runs):
        notes.append("partial: some runs have no events (older runs or events disabled)")

    # ---- tool calls
    calls = [ev for _, ev in evs if ev.get("kind") == "tool.call"]
    run_ids = {r.run for r in runs}
    by_run: dict[str, list[dict]] = defaultdict(list)
    outside: list[dict] = []
    for c in calls:
        if c.get("run") in run_ids and c.get("trace") in (None, tid):
            by_run[str(c["run"])].append(c)
        elif c.get("trace") == tid:
            outside.append(c)
    for r in runs:
        mine = by_run.get(r.run, [])
        shared = [t for t in (r.traces or []) if t != tid]
        items.append({"t": r.start, "order": 2, "kind": "run", "agent": r.agent, **r.to_dict(),
                      "tool_calls": _calls_summary(mine), "shared_with": shared})
    for c in outside:
        t = _ts(c.get("ts")) or t0
        items.append({"t": t, "order": 3, "kind": "tool", "agent": c.get("actor") or ROOT, "tool": c.get("tool"),
                      "ok": c.get("ok"), "ms": c.get("ms"), "error": _clip(c.get("error") or "", 500),
                      "error_type": c.get("error_type"), "run": c.get("run")})
    # ---- lifecycle events that explain waits (a pause, a stall nudge, an orphaned run) of the request or its team
    for t, ev in evs:
        k = ev.get("kind")
        if k not in ("agent.pause", "agent.resume", "agent.failure", "stall.nudge", "run.orphan"):
            continue
        who = ev.get("agent") or ev.get("to")
        stamp = t.strftime("%Y%m%dT%H%M%S%f")
        if ev.get("trace") == tid or (who in members and in_windows(stamp)):
            items.append({"t": t, "order": 4, "kind": "event", "agent": who or "runtime", "event": k,
                          "detail": {x: y for x, y in ev.items() if x not in ENVELOPE}})
    items.sort(key=lambda i: (i["t"], i["order"]))

    # ---- totals
    user_ms = _user_wait(org, [m for m, _ in in_trace.values()], evs, tid, t_end)
    run_ms = sum(r.duration_ms or 0 for r in runs)
    queue_ms = sum(r.queue_ms or 0 for r in runs)
    all_calls = [c for rid in by_run for c in by_run[rid]] + outside
    given = sum(t.budget for t in chain) + sum(m.budget for m in msgs.values() if m.sender == ROOT and m.type == "note"
                                               and m.to in members and in_windows(m.id))
    per_task = []
    for (t, r), (a, b) in zip(steps, windows):
        mine = [x for x in runs if _in_window(x.run.rpartition("@")[2], a, b)]
        per_task.append({"task": t.id, "title": t.title, "state": r.status if r is not None else "open", "runs": len(mine),
                         "budget": t.budget})
    returned = sum(r.budget for _, r in steps if r is not None and r.status in ("done", "failed"))
    totals = {
        "wall_ms": max(0.0, _ms(t0, t_end)), "runs": len(runs), "run_ms": run_ms, "queue_ms": queue_ms,
        "user_wait_ms": user_ms, "tool_calls": len(all_calls),
        "refusals": sum(1 for c in all_calls if c.get("ok") is False),
        "outcomes": dict(Counter(r.outcome for r in runs)),
        "budget_given": given, "budget_used": len(runs), "budget_returned": returned, "tasks": per_task,
    }
    return {"task": tid, "title": task.title, "assignee": task.to, "state": state, "partial": any(n != redirect for n in notes),
            "notes": notes, "start": _iso(t0), "end": _iso(t_end) if final else None, "team": team,
            "window": {"start": start21, "end": end21}, "items": [_plain(i) | {"rel_ms": max(0.0, _ms(t0, i["t"]))} for i in items],
            "totals": totals}


def _user_wait(org: Org, in_trace: list[Msg], evs, tid: str, t_end: datetime) -> float:
    """Milliseconds the request spent waiting on root: from each item that needed the human (an unread-and-waking
    blocked/failed result or any waking note/notice addressed to root) to root's next action on the request (a message
    root sent into it, or a state-changing tool call it made for it); open ends run to the end of the request."""
    asks = sorted(m.t for m in in_trace if m.to == ROOT and m.wake and not (m.type == "result" and m.status == "done")
                  and m.type in ("result", "note"))
    acts = sorted([m.t for m in in_trace if m.sender == ROOT]
                  + [t for t, ev in evs if ev.get("kind") == "tool.call" and ev.get("actor") == ROOT and ev.get("trace") == tid
                     and ev.get("tool") not in READ_ONLY_TOOLS])
    spans: list[tuple[datetime, datetime]] = []
    for a in asks:
        nxt = next((x for x in acts if x > a), None)
        spans.append((a, min(nxt, t_end) if nxt else t_end))
    total, cur_lo, cur_hi = 0.0, None, None
    for lo, hi in sorted(spans):
        if hi <= lo:
            continue
        if cur_hi is None or lo > cur_hi:
            if cur_hi is not None:
                total += _ms(cur_lo, cur_hi)
            cur_lo, cur_hi = lo, hi
        else:
            cur_hi = max(cur_hi, hi)
    if cur_hi is not None:
        total += _ms(cur_lo, cur_hi)
    return total


def render_trace(tr: dict, max_lines: int | None = None) -> str:
    t = tr["totals"]
    head = f'trace {tr["task"]} "{tr["title"]}" -> {tr["assignee"]}: {tr["state"]}' + ("  [partial]" if tr["partial"] else "")
    lines: list[str] = []
    for it in tr["items"]:
        pad = "  " * Org.depth(it["agent"]) if it.get("agent") else ""
        rel = f'{fmt_rel(it["rel_ms"]):>8}  '
        k = it["kind"]
        if k == "message":
            mark = "" if it["trace_source"] == "recorded" else "~"
            text = f'{it["from"]} -> {it["to"]} {it["type"]}' + (f' ({it["status"]})' if it.get("status") else "")
            text += f' "{_clip(it["title"], 60)}"' if it.get("title") else ""
            text += f' +{it["budget"]} run(s)' if it.get("budget") else ""
            lines.append(f"{rel}{pad}{mark}{text}")
        elif k == "run":
            calls = it["tool_calls"]
            bits = [it["outcome"]]
            if it.get("duration_ms") is not None:
                bits.append(f'ran {fmt_dur(it["duration_ms"])}')
            if it.get("queue_ms") is not None:
                bits.append(f'queued {fmt_dur(it["queue_ms"])}')
            if it["source"] == "events":
                tools = " ".join(f"{n}×{c}" for n, c in sorted(calls["by_tool"].items(), key=lambda kv: (-kv[1], kv[0])))
                bits.append(f'{calls["total"]} call(s)' + (f" [{tools}]" if tools else "")
                            + (f', {len(calls["refused"])} refused' if calls["refused"] else ""))
            if it.get("shared_with"):
                bits.append(f"shared with {len(it['shared_with'])} other request(s)")
            if it.get("error"):
                bits.append(f'error: {_clip(it["error"], 120)}')
            lines.append(f'{rel}{pad}run {it["run"].split("@", 1)[-1]} {", ".join(bits)}')
            for r in calls["refused"]:
                lines.append(f'{"":>10}{pad}  ! {r["tool"]}: {_clip(r["error"], 200)}')
        elif k == "tool":
            ok = "ok" if it.get("ok") else f'REFUSED: {_clip(it.get("error") or "", 200)}'
            lines.append(f'{rel}{pad}{it["agent"]} {it["tool"]} {ok}')
        else:
            d = it["detail"]
            lines.append(f'{rel}{pad}* {it["event"]} {_clip(" ".join(f"{a}={b}" for a, b in d.items() if b not in (None, "")), 160)}')
    foot = (f'totals: wall {fmt_dur(t["wall_ms"])} | runs {t["runs"]} (budget given {t["budget_given"]}, '
            f'returned {t["budget_returned"]}) | run time {fmt_dur(t["run_ms"])} | queue {fmt_dur(t["queue_ms"])} | '
            f'waiting on you {fmt_dur(t["user_wait_ms"])} | tool calls {t["tool_calls"]} ({t["refusals"]} refused)')
    out = [head, *_cap(lines, max_lines, f"observe events --trace {tr['task']} (agent=/kind=/errors)")]
    if len(t.get("tasks") or ()) > 1:  # reworks: each task's runs are what `progress` reports for it
        out.append("tasks: " + " | ".join(f'{x["task"]} "{_clip(x["title"], 30)}" {x["state"]} {x["runs"]} run(s)' for x in t["tasks"]))
    out.append(foot)
    out += [f"note: {n}" for n in tr["notes"]]
    return "\n".join(out)


# ============================================================================================ metrics

_ID = re.compile(r"\b\d{8}T\d{6,}[\w.-]*")
_PATH = re.compile(r"(?<![\w.])(?:/[\w.@+~-]+){2,}/?|(?<![\w/])[\w.-]+(?:/[\w.-]+)*\.\w{1,6}\b")
_QUOTED = re.compile(r'"[^"]*"|\'[^\']*\'')
_HEX = re.compile(r"\b[0-9a-f]{8,}\b")
_NUM = re.compile(r"\b\d+\b")


def normalize_refusal(text: str) -> str:
    """A refusal text with what varies removed (message ids, paths, quoted titles, hashes, numbers), so identical
    reasons group together."""
    t = _ID.sub("<id>", str(text))
    t = _QUOTED.sub("<text>", t)
    t = _PATH.sub("<path>", t)
    t = _HEX.sub("<hex>", t)
    t = _NUM.sub("N", t)
    return _clip(t, 160)


def _group_key(by: str, kind: str, obj, msgs: dict[str, Msg]) -> list[str]:
    """Group keys of a run (``kind='run'``) or a tool call (``'call'``) for ``by``; [] means no row."""
    if by == "agent":
        return [obj.agent] if kind == "run" else [str(obj.get("actor") or "-")]
    if by == "tool":
        return [str(obj.get("tool"))] if kind == "call" else []
    if by == "service":
        if kind == "call":
            svc = (obj.get("args") or {}).get("service")
            return [str(svc)] if svc else ["-"]
        svcs = {msgs[b].service for b in obj.batch or () if b in msgs and msgs[b].service}
        return sorted(svcs) or ["-"]
    if by == "trace":
        if kind == "call":
            return [str(obj.get("trace") or "-")]
        return list(obj.traces or []) or ["-"]
    raise OrgError("by must be one of agent, tool, service, trace")


def metrics(org: Org, since="24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> dict:
    """Counts, rates and percentiles over ``[since, now]``.

    Runs are the run logs of the window (so counts equal what the files say), with outcome and duration from
    ``run.end`` events (else from the log's closing lines). Percentiles are nearest-rank on the raw durations.
    ``by``: agent | tool | service | trace adds a table grouped that way. ``agent`` restricts to one agent.
    """
    now = _aware(now) or utcnow()
    lo = parse_when(since, now) or (now - timedelta(hours=24))
    if by is not None and by not in ("agent", "tool", "service", "trace"):
        raise OrgError("by must be one of agent, tool, service, trace")
    agent = Org.norm(agent) if agent else None
    later = list(timed_events(org, lo, None))  # run.end of a run that started in the window may come after it
    evs = [(t, ev) for t, ev in later if t <= now]
    runs = collect_runs(org, lo, now, run_events(later))
    if agent:
        runs = [r for r in runs if r.agent == agent]
    calls = [ev for _, ev in evs if ev.get("kind") == "tool.call" and (not agent or ev.get("actor") == agent)]
    outcomes = Counter(r.outcome for r in runs)
    run_ms = [r.duration_ms for r in runs if r.duration_ms is not None]
    queue = [r.queue_ms for r in runs if r.queue_ms is not None]

    tools: dict[str, dict] = {}
    for name in sorted({str(c.get("tool")) for c in calls}):
        mine = [c for c in calls if str(c.get("tool")) == name]
        bad = [c for c in mine if c.get("ok") is False]
        ms = [float(c["ms"]) for c in mine if isinstance(c.get("ms"), (int, float))]
        tools[name] = {"calls": len(mine), "refused": len(bad), "refusal_rate": len(bad) / len(mine),
                       "ms": _stats(ms), "exceptions": sum(1 for c in bad if c.get("error_type") not in (None, "OrgError"))}
    refused = [c for c in calls if c.get("ok") is False]
    groups: dict[str, dict] = {}
    for c in refused:
        g = groups.setdefault(normalize_refusal(c.get("error") or "(no text)"), {"count": 0, "example": c.get("error"), "tools": Counter()})
        g["count"] += 1
        g["tools"][str(c.get("tool"))] += 1
    top = sorted(groups.items(), key=lambda kv: (-kv[1]["count"], kv[0]))[:10]

    kinds = Counter(str(ev.get("kind")) for _, ev in evs)
    msgs = build_messages(scan_messages(org))
    in_window = [m for m in msgs.values() if lo <= m.t <= now]
    sched_err = Counter(str(ev.get("phase")) for _, ev in evs if ev.get("kind") == "scheduler.error")
    exits = Counter(_clip(ev.get("reason"), 80) for _, ev in evs if ev.get("kind") == "scheduler.exit")
    pauses = Counter(_clip(ev.get("reason"), 40) for _, ev in evs if ev.get("kind") == "agent.pause")
    out: dict = {
        "since": _iso(lo), "until": _iso(now), "events": sum(kinds.values()), "agent": agent,
        "runs": {"total": len(runs), **{k: outcomes.get(k, 0) for k in ("ok", "failed", "timeout", "killed", "running", "unknown")},
                 "duration_ms": _stats(run_ms), "queue_ms": _stats(queue)},
        "tool_calls": {"total": len(calls), "refused": len(refused), "refusal_rate": (len(refused) / len(calls)) if calls else 0.0,
                       "by_tool": tools},
        "top_refusals": [{"message": k, "count": v["count"], "example": _clip(v["example"] or "", 300),
                          "tools": dict(v["tools"])} for k, v in top],
        "messages": dict(Counter(m.type for m in in_window)),
        "stalls": kinds.get("stall.nudge", 0), "pauses": {"total": sum(pauses.values()), "by_reason": dict(pauses)},
        "agent_failures": kinds.get("agent.failure", 0), "orphans": kinds.get("run.orphan", 0),
        "scheduler": {"starts": kinds.get("scheduler.start", 0), "errors": dict(sched_err), "exits": dict(exits)},
        "budget_spent": len(runs),
    }
    if by:
        rows: dict[str, dict] = {}

        def row(key: str) -> dict:
            return rows.setdefault(key, {"key": key, "runs": [], "ok": 0, "bad": 0, "calls": [], "refused": 0})

        for r in runs:
            for key in _group_key(by, "run", r, msgs):
                x = row(key)
                x["runs"].append(r)
                x["ok"] += r.outcome == "ok"
                x["bad"] += r.outcome in ("failed", "timeout", "killed")
        for c in calls:
            for key in _group_key(by, "call", c, msgs):
                x = row(key)
                x["calls"].append(c)
                x["refused"] += c.get("ok") is False
        table = []
        for key, x in sorted(rows.items()):
            durs = [r.duration_ms for r in x["runs"] if r.duration_ms is not None]
            ms = [float(c["ms"]) for c in x["calls"] if isinstance(c.get("ms"), (int, float))]
            table.append({"key": key, "runs": len(x["runs"]), "ok": x["ok"], "failed": x["bad"],
                          "run_ms": _stats(durs), "calls": len(x["calls"]), "refused": x["refused"],
                          "refusal_rate": (x["refused"] / len(x["calls"])) if x["calls"] else 0.0, "call_ms": _stats(ms)})
        out["by"] = {"dimension": by, "rows": table}
    return out


def render_metrics(m: dict, limit: int = 50) -> str:
    r, tc = m["runs"], m["tool_calls"]
    lines = [f'metrics {m["since"][:19]}Z .. {m["until"][:19]}Z' + (f' agent={m["agent"]}' if m.get("agent") else "")
             + f' ({m["events"]} event(s) in the window)']
    d, q = r["duration_ms"], r["queue_ms"]
    lines.append(f'runs {r["total"]}: ok {r["ok"]}, failed {r["failed"]}, timeout {r["timeout"]}, killed {r["killed"]}'
                 + (f', running {r["running"]}' if r["running"] else "") + (f', unknown {r["unknown"]}' if r["unknown"] else "")
                 + f' | duration p50 {fmt_dur(d["p50"])} p95 {fmt_dur(d["p95"])} max {fmt_dur(d["max"])} (n={d["n"]})'
                 + f' | queue p50 {fmt_dur(q["p50"])} p95 {fmt_dur(q["p95"])} (n={q["n"]})')
    lines.append(f'budget spent {m["budget_spent"]} run(s)')
    lines.append(f'tool calls {tc["total"]}, refused {tc["refused"]} ({tc["refusal_rate"]:.1%})')
    for name, t in sorted(tc["by_tool"].items(), key=lambda kv: (-kv[1]["calls"], kv[0]))[:limit]:
        lines.append(f'  {name:<16} {t["calls"]:>5} calls {t["refused"]:>3} refused ({t["refusal_rate"]:.0%})'
                     f' p50 {fmt_dur(t["ms"]["p50"])} p95 {fmt_dur(t["ms"]["p95"])}'
                     + (f' [{t["exceptions"]} exception(s)]' if t["exceptions"] else ""))
    if m["top_refusals"]:
        lines.append("top refusals:")
        lines += [f'  {x["count"]}x {x["message"]}  ({", ".join(f"{k}x{v}" for k, v in x["tools"].items())})' for x in m["top_refusals"]]
    lines.append("messages: " + (", ".join(f"{k} {v}" for k, v in sorted(m["messages"].items())) or "none"))
    s = m["scheduler"]
    lines.append(f'scheduler: {s["starts"]} start(s); errors: ' + (", ".join(f"{k} x{v}" for k, v in s["errors"].items()) or "none")
                 + "; exits: " + (", ".join(f"{k} x{v}" for k, v in s["exits"].items()) or "none"))
    lines.append(f'stalls {m["stalls"]}, pauses {m["pauses"]["total"]}'
                 + (f' ({", ".join(f"{k} x{v}" for k, v in m["pauses"]["by_reason"].items())})' if m["pauses"]["total"] else "")
                 + f', agent failures {m["agent_failures"]}, orphaned runs {m["orphans"]}')
    if m.get("by"):
        b = m["by"]
        lines.append(f'by {b["dimension"]}:')
        rows = b["rows"]
        for x in rows[:limit]:
            runs_part = (f'runs {x["runs"]:>3} (ok {x["ok"]}, bad {x["failed"]}) run p50 {fmt_dur(x["run_ms"]["p50"])}'
                         f' p95 {fmt_dur(x["run_ms"]["p95"])} | ') if b["dimension"] != "tool" else ""
            calls_part = (f'calls {x["calls"]:>4} refused {x["refused"]} ({x["refusal_rate"]:.0%})'
                          f' p50 {fmt_dur(x["call_ms"]["p50"])} p95 {fmt_dur(x["call_ms"]["p95"])}')
            lines.append(f'  {_clip(x["key"], 48):<48} {runs_part}{calls_part}')
        if len(rows) > limit:
            lines.append(f"... {len(rows) - limit} more row(s), narrow with since/agent")
    if not m["events"]:
        lines.append("(no events in this window: run counts come from the run logs; tool calls and queue waits need events)")
    return "\n".join(lines)


# ============================================================================================ now


def _tail_events(path: Path, nbytes: int = 65536) -> list[dict]:
    try:
        with open(path, "rb") as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - nbytes))
            data = f.read()
    except OSError:
        return []
    lines = data.splitlines()
    if size > nbytes and lines:
        lines = lines[1:]  # the first line is cut
    out = []
    for raw in lines:
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        if isinstance(ev, dict):
            out.append(ev)
    return out


def _scheduler_files(org: Org) -> list[tuple[int, int, Path]]:
    """(start_epoch_ms, pid, path) of every scheduler event file, newest process first."""
    out = []
    for d in reversed(_day_dirs(org, None, None)):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            m = re.fullmatch(r"scheduler-(\d+)-(\d+)\.jsonl", n)
            if m:
                out.append((int(m.group(2)), int(m.group(1)), d / n))
    return sorted(out, key=lambda x: (x[0], str(x[2])), reverse=True)


def _scheduler_info(org: Org, now: datetime) -> dict:
    st = scheduler_state(org)
    info: dict = {"state": st.state, "pid": st.pid, "since": st.since, "detail": st.detail, "mode": None,
                  "uptime_s": None, "last_heartbeat_age_s": None, "last_exit": None, "heartbeats": False}
    files = _scheduler_files(org)
    if st.state == "running" and st.pid is not None:
        mine = [f for f in files if f[1] == st.pid]
        if mine:
            _, _, path = mine[0]
            tail = _tail_events(path)
            head = _head_event(path)
            start = head if head and head.get("kind") == "scheduler.start" else next((e for e in tail if e.get("kind") == "scheduler.start"), None)
            if start:
                info["mode"] = start.get("mode")
                t = _ts(start.get("ts"))
                info["uptime_s"] = (now - t).total_seconds() if t else None
            beats = [e for e in tail if e.get("kind") == "scheduler.heartbeat"]
            if beats:
                t = _ts(beats[-1].get("ts"))
                info["heartbeats"] = True
                info["last_heartbeat_age_s"] = max(0.0, (now - t).total_seconds()) if t else None
                info["heartbeat_running"] = beats[-1].get("running")
    else:
        for _, _, path in files[:3]:
            exits = [e for e in _tail_events(path) if e.get("kind") == "scheduler.exit"]
            if exits:
                info["last_exit"] = _clip(exits[-1].get("reason"), 160)
                info["last_exit_ts"] = exits[-1].get("ts")
                break
        if not info["last_exit"]:
            try:
                reason = (org.root / EXIT_FILE).read_text(encoding="utf-8").strip()
            except OSError:
                reason = ""
            info["last_exit"] = reason or None
    return info


def _head_event(path: Path) -> dict | None:
    try:
        with open(path, "rb") as f:
            line = f.readline()
        ev = json.loads(line)
        return ev if isinstance(ev, dict) else None
    except (OSError, ValueError):
        return None


def now_view(org: Org, now: datetime | None = None) -> dict:
    """What is happening right now. Works with no events (then the event-derived parts are empty)."""
    from .progress import _human_items

    now = _aware(now) or utcnow()
    cfg = org.config
    max_parallel = config_number(cfg, "max_parallel", int)
    sched = _scheduler_info(org, now)
    running_rec = _running_ledger(org)
    agents = org.agents()
    inflight = [a for a in agents if org.running(a)]
    batches: dict[str, list[dict]] = {}
    for a in inflight:
        d = org.dir(a) / "inflight"
        recs = []
        for n in sorted(os.listdir(d)) if d.is_dir() else []:
            if n.endswith(".md") and not n.startswith("."):
                meta, err, _ = _read_meta(d / n)
                if meta:
                    recs.append({"id": str(meta.get("id") or n[:-3]), "title": str(meta.get("title") or ""),
                                 "from": str(meta.get("from") or ""), "trace": str(meta["trace"]) if meta.get("trace") else None})
        batches[a] = recs
    traces_idx = None
    if inflight or any(org.unread(a) for a in agents):
        msgs = build_messages(scan_messages(org))
        traces_idx = Traces(org, msgs)
    runs_now = []
    for a in inflight:
        rec = running_rec.get(a) or {}
        started = rec.get("started")
        stem = Path(str(rec.get("log", ""))).stem if rec.get("log") else None
        if stem is None:
            logs = _run_logs(org, a)
            stem = logs[-1][0] if logs else None
        t0 = datetime.fromtimestamp(started, timezone.utc) if isinstance(started, (int, float)) else (_stamp(stem or "") if stem else None)
        traces = sorted({t for b in batches[a] if (t := b["trace"] or (traces_idx.of(b["id"])[0] if traces_idx else None))})
        runs_now.append({"agent": a, "run": f"{a}@{stem}" if stem else None, "elapsed_s": (now - t0).total_seconds() if t0 else None,
                         "batch": [b["title"] or b["id"] for b in batches[a]], "traces": traces})
    queued = []
    free = max_parallel - len(inflight)
    sched_up = sched["state"] == "running"
    for a in agents:
        n = org.unread(a)
        if not n:
            continue
        paused, budget = org.paused(a), org.budget(a) or 0
        if org.running(a):  # mail that arrived during a run waits for the next one (one run per agent at a time)
            reason = "its current run is still going; the next run starts after it"
        elif paused and not (paused == "budget" and budget > 0):
            reason = f"paused: {paused}"
        elif budget <= 0:
            reason = "no budget"
        elif not sched_up:
            reason = "scheduler is not running"
        elif free <= 0:
            reason = f"max_parallel ({max_parallel}) runs are busy"
        else:
            reason = "ready: starts on the next tick"
        inbox = org.dir(a) / "inbox"
        oldest = min((t for p in inbox.glob("*.md") if not p.name.startswith(".") and (t := _stamp(p.name))), default=None)
        queued.append({"agent": a, "unread": n, "reason": reason, "waiting_s": (now - oldest).total_seconds() if oldest else None})
    needs = [line for _, line in _human_items(org)]
    since = now - ERROR_WINDOW
    errs = [ev for ev in iter_events(org, since, now) if is_error(ev)]
    last_event = None
    for p in event_files(org, now - timedelta(days=2), None)[-3:]:
        for ev in _tail_events(p, 8192)[-1:]:
            t = _ts(ev.get("ts"))
            if t and (last_event is None or t > last_event):
                last_event = t
    return {"now": _iso(now), "scheduler": sched, "max_parallel": max_parallel, "runs_in_flight": runs_now,
            "queued": queued, "waiting_on_you": needs, "open_root_tasks": len(org.outstanding(ROOT)),
            "paused": {a: org.paused(a) for a in agents if org.paused(a)},
            "errors_15m": {"count": len(errs), "events": errs[-5:]}, "last_event": _iso(last_event),
            "events_seen": last_event is not None}


def render_now(v: dict, max_lines: int | None = None) -> str:
    s = v["scheduler"]
    if s["state"] == "running":
        bits = [b for b in (s.get("mode"), f'up {fmt_dur(s["uptime_s"] * 1000)}' if s.get("uptime_s") is not None else None) if b]
        if s.get("last_heartbeat_age_s") is not None:
            bits.append(f'last heartbeat {fmt_dur(s["last_heartbeat_age_s"] * 1000)} ago')
        elif s.get("uptime_s") is not None:
            bits.append("no heartbeat seen")
        line = f'scheduler: running pid {s["pid"]}' + (f' ({", ".join(bits)})' if bits else "")
    elif s["state"] == "unverified":
        line = f'scheduler: unverified - pid file names pid {s["pid"]} ({s["detail"]})'
    else:
        line = "scheduler: stopped" + (f' (last exit: {s["last_exit"]})' if s.get("last_exit") else "")
    lines = [line, f'runs in flight {len(v["runs_in_flight"])}/{v["max_parallel"]}' + (":" if v["runs_in_flight"] else "")]
    for r in v["runs_in_flight"]:
        lines.append(f'  {r["agent"]} {fmt_dur((r["elapsed_s"] or 0) * 1000)} {_clip(", ".join(r["batch"]), 80)}'
                     + (f' trace {", ".join(r["traces"])}' if r["traces"] else ""))
    if v["queued"]:
        lines.append(f'queued, not running ({len(v["queued"])}):')
        for q in v["queued"]:
            lines.append(f'  {q["agent"]}: {q["unread"]} unread' + (f', oldest {fmt_dur(q["waiting_s"] * 1000)}' if q["waiting_s"] is not None else "")
                         + f' - {q["reason"]}')
    else:
        lines.append("queued, not running: none")
    if v["waiting_on_you"]:
        lines.append(f'waiting on you ({len(v["waiting_on_you"])}):')
        lines += [f"  {x}" for x in v["waiting_on_you"]]
    else:
        lines.append("waiting on you: nothing")
    e = v["errors_15m"]
    lines.append(f'errors in the last 15 min: {e["count"]}' + ("" if v["events_seen"] else " (no events recorded in this organization)"))
    lines += [f"  {format_event(ev, 200)}" for ev in e["events"]]
    if v["paused"]:
        lines.append("paused: " + ", ".join(f"{a} ({r})" for a, r in v["paused"].items()))
    return "\n".join(_cap(lines, max_lines, "observe events errors_only=true"))


# ============================================================================================ check


def _check(cid: str, name: str, problems: list[str], note: str = "", limit: int = 8) -> dict:
    details = problems[:limit] + ([f"... and {len(problems) - limit} more"] if len(problems) > limit else [])
    return {"id": cid, "name": name, "ok": not problems, "details": details or ([note] if note else [])}


def _live_run(org: Org, rec: dict | None) -> bool:
    if not rec:
        return False
    return judge_orphan(rec) in ("ours", "doubt")


def _check_messages(org: Org, files: list[FileRec], now: float) -> dict:
    problems: list[str] = []
    rel = lambda p: str(p.relative_to(org.root))  # noqa: E731
    sent: dict[str, list[FileRec]] = defaultdict(list)
    recv: dict[str, list[FileRec]] = defaultdict(list)
    for f in files:
        if f.error:
            problems.append(f"{rel(f.path)}: {f.error}")
            continue
        if f.path.stem != f.id:
            problems.append(f"{rel(f.path)}: file name differs from its id {f.id}")
        (sent if f.box == "sent" else recv)[f.id].append(f)
        meta = f.meta or {}
        if f.box == "sent" and Org.norm(str(meta.get("from"))) != f.owner:
            problems.append(f"{rel(f.path)}: in the sent/ of {f.owner} but from {meta.get('from')}")
        if f.box != "sent" and Org.norm(str(meta.get("to"))) != f.owner:
            problems.append(f"{rel(f.path)}: in the {f.box}/ of {f.owner} but addressed to {meta.get('to')}")
    for mid, fs in sent.items():
        if len(fs) > 1:
            problems.append(f"id {mid} appears {len(fs)} times in sent/ ({', '.join(f.owner for f in fs)})")
    for mid, fs in recv.items():
        if len(fs) > 1:
            problems.append(f"id {mid} appears {len(fs)} times among received copies ({', '.join(f'{f.owner}/{f.box}' for f in fs)})")
    for mid, fs in sent.items():
        f = fs[0]
        to = Org.norm(str((f.meta or {}).get("to")))
        if mid not in recv and org.exists(to) and now - f.mtime > COPY_GRACE:
            problems.append(f"{mid}: sent by {f.owner} to {to} but {to} has no copy (recover() or a run start re-delivers it)")
    for mid, fs in recv.items():
        f = fs[0]
        sender = Org.norm(str((f.meta or {}).get("from")))
        if mid not in sent and sender != RUNTIME and org.exists(sender) and now - f.mtime > COPY_GRACE:
            problems.append(f"{mid}: in {f.owner}/{f.box} from {sender} but {sender} has no sent copy")
    n = len(sent) + len({k for k in recv if k not in sent})
    return _check("a", "messages intact: files parse, ids unique, sender and recipient copies match", problems,
                  f"{n} message(s) checked")


def _retired_trees(org: Org) -> list[tuple[Path, bool]]:
    """(directory, was a top-level agent) of every retired tree; the top-level ones are named without a dot before
    the ``-<timestamp>`` suffix (the address with ``/`` turned into ``.``)."""
    base = org.root / ".retired"
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    out = []
    for n in names:
        if (base / n).is_dir():
            out.append((base / n, "." not in re.sub(r"-\d{8}T\d{6}$", "", n)))
    return out


def _sum_budget(d: Path) -> int:
    total = 0
    try:
        names = os.listdir(d)
    except OSError:
        return 0
    for n in names:
        if n.endswith(".md") and not n.startswith("."):
            meta, err, _ = _read_meta(d / n)
            if meta and not err:
                total += int(meta.get("budget") or 0)
    return total


def _tree_unspent(top: Path) -> int:
    """Budget a retired tree still held when it was retired: for each agent directory in it, what it received (inbox,
    inflight, read) - what it sent - its run logs."""
    total = 0
    for here, dirs, files in os.walk(top):
        base = os.path.basename(here)
        if base in (*BOXES, "runs", "work", "services") or base.startswith("."):
            dirs.clear()
            continue
        if "AGENT.md" in files:
            h = Path(here)
            total += sum(_sum_budget(h / b) for b in RECV_BOXES) - _sum_budget(h / "sent")
            runs = h / "runs"
            total -= sum(1 for n in (os.listdir(runs) if runs.is_dir() else []) if n.endswith(".log") and not n.startswith("."))
    return total


def _check_budget(org: Org, files: list[FileRec], now: float) -> dict:
    """Budget conservation.

    Budget is derived from messages and run logs (``Org.budget`` = received - handed down - run logs). Runs of budget
    enter only from root (a task's or a note's ``budget`` in root's ``sent/``); they leave in four ways, and nothing
    else: held by an agent now (the sum of ``Org.budget``), consumed (run logs of live agents, and of retired
    agents, see ``review.retired_runs``), returned to root (the ``budget`` of messages root received: results and
    notes), or dropped when a top-level agent was retired (root has no limit, so its team's unspent runs are not
    refunded; retired deeper in the tree they are refunded to the parent by a runtime note, which cancels out).
    Hence::

        handed down by root == held + used (live + retired) + returned to root + dropped at retirement

    A message being delivered right now (sender copy written, recipient copy not yet, younger than ``COPY_GRACE``) is
    charged but not yet credited; it is counted as "in delivery" so a live check does not fail on it.
    """
    handed = sum(int((f.meta or {}).get("budget") or 0) for f in files if not f.error and f.owner == ROOT and f.box == "sent")
    returned = sum(int((f.meta or {}).get("budget") or 0) for f in files if not f.error and f.owner == ROOT and f.box in RECV_BOXES)
    try:
        held = sum(org.budget(a) or 0 for a in org.agents())
    except Exception as exc:  # noqa: BLE001 - a corrupt message makes the arithmetic impossible; (a) names the file
        return _check("b", "budget conserved", [f"cannot compute the agents' budgets: {type(exc).__name__}: {exc}"])
    used_live = sum(org.runs_used(a) for a in org.agents())
    used_retired = retired_runs(org)
    dropped = sum(_tree_unspent(top) for top, is_top in _retired_trees(org) if is_top)
    delivered = {f.id for f in files if not f.error and f.box in RECV_BOXES}
    pending = sum(int((f.meta or {}).get("budget") or 0) for f in files if not f.error and f.box == "sent"
                  and f.id not in delivered and now - f.mtime <= COPY_GRACE and org.exists(Org.norm(str(f.meta.get("to")))))
    rhs = held + used_live + used_retired + returned + dropped + pending
    eq = (f"handed down {handed} = held {held} + used {used_live} live + {used_retired} retired "
          f"+ returned {returned} + dropped {dropped}" + (f" + {pending} in delivery" if pending else ""))
    if handed == rhs:
        return _check("b", "budget conserved: handed down = held + used + returned (+ dropped at retirement)", [], eq)
    diff = handed - rhs
    return _check("b", "budget conserved: handed down = held + used + returned (+ dropped at retirement)",
                  [f"{eq}: {abs(diff)} run(s) {'vanished' if diff > 0 else 'appeared from nowhere'} (difference {diff:+d})"])


def _check_inflight(org: Org, now: float) -> dict:
    st = scheduler_state(org)
    running = _running_ledger(org)
    problems = []
    for a in org.agents():
        d = org.dir(a) / "inflight"
        files = [d / n for n in (os.listdir(d) if d.is_dir() else []) if n.endswith(".md") and not n.startswith(".")]
        if not files:
            continue
        if _live_run(org, running.get(a)):
            continue
        age = max((now - p.stat().st_mtime for p in files if p.exists()), default=0.0)
        if st.state == "running" and age <= INFLIGHT_GRACE:
            continue  # the scheduler has just begun this run
        problems.append(f"{a}: {len(files)} message(s) inflight for {fmt_dur(age * 1000)} but no live run"
                        + (" (no scheduler is running)" if st.state != "running" else " (the scheduler has no live process for it)"))
    return _check("c", "nothing inflight without a live run", problems, "no agent has an unfinished batch without a run")


def _check_runs(org: Org) -> dict:
    running = _running_ledger(org)
    problems: list[str] = []
    started: dict[str, dict] = {}
    done: set[str] = set()
    first: datetime | None = None
    n_start = 0
    for t, ev in timed_events(org):
        k = ev.get("kind")
        if k == "scheduler.start" and (first is None or t < first):
            first = t
        elif k == "run.start" and ev.get("run"):
            started[str(ev["run"])] = ev
            n_start += 1
            if first is None or t < first:
                first = t
        elif k in ("run.end", "run.orphan") and ev.get("run"):
            done.add(str(ev["run"]))
    if first is None:
        return _check("d", "runs accounted for: run.start has run.end or a live process; run logs have run.start", [],
                      "no run events yet (skipped)")
    for rid, ev in started.items():
        if rid in done:
            continue
        agent = str(ev.get("agent") or rid.rpartition("@")[0])
        rec = running.get(agent)
        if rec and Path(str(rec.get("log", ""))).stem == rid.rpartition("@")[2] and _live_run(org, rec):
            continue
        problems.append(f"{rid}: run.start at {ev.get('ts')} has no run.end and no live process")
    for agent in org.agents():
        for stem, path in _run_logs(org, agent):
            t = _stamp(stem)
            if t is None or t < first or f"{agent}@{stem}" in started:
                continue
            if org.runtime.run_log_reader.facts(path).get("failed_start"):
                continue  # a run that never started has no run.start by design
            problems.append(f"{agent}@{stem}: run log without a run.start event (events began {first.isoformat(timespec='seconds')})")
    return _check("d", "runs accounted for: run.start has run.end or a live process; run logs have run.start", problems,
                  f"{n_start} run.start event(s) checked")


def _check_seq(org: Org) -> dict:
    """``seq`` counts the lines of ONE file and restarts at 1 in each day's file: every file is gapless from 1 on its own."""
    problems: list[str] = []
    files = event_files(org)
    for p in sorted(files, key=lambda x: (x.parent.name, x.name)):
        expect = 1
        for _, ev in _read_events(p):
            seq = ev.get("seq")
            if not isinstance(seq, int) or isinstance(seq, bool):
                continue
            if seq != expect:
                where = f"{p.parent.name}/{p.name}"
                problems.append(f"{where}: first seq is {seq}, expected 1" if expect == 1 else
                                f"{where}: seq jumps from {expect - 1} to {seq} ({seq - expect} line(s) lost)" if seq > expect else
                                f"{where}: seq goes back from {expect - 1} to {seq}")
                if len(problems) >= 50:
                    break
            expect = seq + 1
    return _check("e", "event files have no seq gaps", problems, f"{len(files)} event file(s) checked")


def _check_pidfile(org: Org) -> dict:
    pidfile = org.root / ".runtime" / "scheduler.pid"
    if not pidfile.exists():
        return _check("f", "scheduler pid file matches a live scheduler", [], "no pid file: no scheduler claims to run")
    st = scheduler_state(org)
    if st.state == "running":
        return _check("f", "scheduler pid file matches a live scheduler", [], f"pid {st.pid} is this organization's scheduler")
    if st.state == "unverified":
        return _check("f", "scheduler pid file matches a live scheduler",
                      [f".runtime/scheduler.pid names pid {st.pid}, alive but not verified as this org's scheduler ({st.detail})"])
    return _check("f", "scheduler pid file matches a live scheduler",
                  [".runtime/scheduler.pid is stale: its process is gone (a scheduler start replaces it; remove it if none will start)"])


def check(org: Org, now: datetime | None = None) -> dict:
    """The invariants of the runtime, each PASS/FAIL with details (read-only):

    (a) every message file parses, ids are unique, each sender copy has a recipient copy and vice versa;
    (b) budget conservation (see :func:`_check_budget` for the equation);
    (c) nothing inflight without a live run;
    (d) every ``run.start`` has a ``run.end`` or a live process, and every run log since events began has a ``run.start``;
    (e) per-file ``seq`` has no gaps;
    (f) the scheduler pid file matches a live scheduler process.
    """
    at = (_aware(now) or utcnow()).timestamp()
    files = scan_messages(org)
    checks = [_check_messages(org, files, at), _check_budget(org, files, at), _check_inflight(org, at),
              _check_runs(org), _check_seq(org), _check_pidfile(org)]
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def render_check(res: dict) -> str:
    lines = []
    for c in res["checks"]:
        lines.append(f'({c["id"]}) {"PASS" if c["ok"] else "FAIL"} {c["name"]}')
        lines += [f"      {d}" for d in c["details"]]
    bad = [c["id"] for c in res["checks"] if not c["ok"]]
    lines.append("all checks passed" if not bad else f'FAILED: {", ".join(bad)}')
    return "\n".join(lines)


# ============================================================================================ entry points

_MSG_ID = re.compile(r"\d{8}T\d{6,}-")


def observe_text(org: Org, view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None,
                 errors_only: bool = False, limit: int = 50, now: datetime | None = None, max_lines: int | None = None) -> str:
    """The text of one view. ``target``: the task id for ``trace``; for ``events`` a trace id, an agent address or an
    event kind (``tool.call``, ``run``); for ``metrics`` an agent. ``limit``: events shown, rows per table."""
    view = (view or "now").strip().lower()
    if view not in VIEWS:
        raise OrgError(f"view must be one of {', '.join(VIEWS)}")
    limit = max(1, int(limit or 50))
    cap = max_lines if max_lines is not None else max(2 * limit, 80)
    if view == "now":
        return render_now(now_view(org, now), cap)
    if view == "check":
        return render_check(check(org, now))
    if view == "trace":
        if not target:
            raise OrgError("trace needs target=<root task id> (see progress for the ids)")
        return render_trace(trace(org, target, now), cap)
    if view == "metrics":
        return render_metrics(metrics(org, since, by, now, agent=target), limit)
    agent = kind = tr = None
    if target:
        if _MSG_ID.match(target):
            tr = target
        elif org.exists(target) or Org.norm(target) in (ROOT, RUNTIME):
            agent = target
        else:
            kind = target
    v = events_view(org, since, None, agent, kind, tr, errors_only, limit, now)
    v["any"] = bool(event_files(org))
    return render_events(v, cap)


def register_observe_tool(mcp, binding) -> None:
    """Register the root-only, read-only MCP tool ``observe``."""

    @mcp.tool()
    def observe(view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None,
                errors_only: bool = False, limit: int = 50) -> str:
        """Read-only look at how the organization is running. view=
        "now": what runs, what is queued and why, what waits on you, errors of the last 15 min.
        "trace" (target=root task id): every message, run, tool call and refusal of one request, with time spent
        queued, running and waiting on you. "metrics" (since=15m|24h|7d|ISO, by=agent|tool|service|trace): runs,
        failures, refusal rates, latency percentiles, budget spent. "events" (target=agent, trace id or kind,
        errors_only): the raw record. "check": is the runtime consistent (budget, messages, stuck runs)?"""
        return observe_text(binding.get(), view, target, since, by, errors_only, limit)
