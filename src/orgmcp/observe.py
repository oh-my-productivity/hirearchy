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

THE BOUNDARY (step C-obs-1 of the refactor, ARCHITECTURE.md 3.31 and 5.10). The first half of this module - the events, the
runs, the traces and the metrics - is the package ``orgmcp.observability``: ``events_view`` / ``events`` / ``follow_events`` /
``trace`` / ``metrics`` / ``collect_runs`` / ``Traces`` below only ask it (through ``app.wire_observability``, over the ports
of ``org.runtime``), and the pure functions are its api. What is still here is the second half, which step C-obs-2 moves:

* ``now``: ``_scheduler_files`` ``_scheduler_info`` ``_tail_events`` ``_head_event`` ``now_view`` (``scheduler_state`` is still read
  from ``orgmcp.scheduler``, ``judge_orphan`` likewise: the tests that replace them are C-obs-2's);
* ``check``: ``_check`` ... ``_check_pidfile`` ``check`` (and ``_live_run``);
* the text: ``render_events`` ``render_trace`` ``render_metrics`` ``render_now`` ``render_check`` ``_cap``;
* the entry points: ``observe_text`` and ``register_observe_tool``.

``now_view`` reads the front matter of a single inflight message from ``org.runtime.resources.meta_cache`` directly (``MessageIndex``
has no single-file method; a method that answers it belongs to ``now`` and goes in with it). Everything else it needs of the first half it
takes from the names below, which are the package's. The default time of every view is the clock of the runtime (``org.runtime.clock``).
"""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import kernel as _kernel
from .app import wire_eventlog
from .app import wire_observability as _wired
from .core import ROOT, RUNTIME, Org, OrgError
from .eventlog import ENVELOPE as _ENVELOPE
from .eventlog import EVENTS_REL, EventFollower, event_file
from .health import _aware, _stamp, config_number
from .mail import MessageFile
from .observability import api as _api
from .scheduler import EXIT_FILE, judge_orphan, scheduler_state

EVENTS_DIR = EVENTS_REL
ERROR_WINDOW = timedelta(minutes=15)
COPY_GRACE = 5.0  # seconds a freshly written message may lack its other copy (delivery writes two files)
INFLIGHT_GRACE = 30.0  # seconds an inflight batch may exist before the run record is written
RECV_BOXES = ("inbox", "inflight", "read")
ENVELOPE = set(_ENVELOPE)
READ_ONLY_TOOLS = _wired.READ_ONLY_TOOLS
VIEWS = ("now", "trace", "metrics", "events", "check")

# ============================================================================================ the vocabulary (the package's)

fmt_dur = _kernel.fmt_dur
fmt_rel = _api.fmt_rel
percentile = _api.percentile
parse_when = _api.parse_when
normalize_refusal = _api.normalize_refusal
is_error = _api.is_error
format_event = _api.format_event
_clip = _kernel.clip_line
_ts = _kernel.parse_time
_iso = _wired.iso
_plain = _wired.plain
_cap = _wired.cap
_matcher = _wired.matcher

# ============================================================================================ the event log


def event_files(org: Org, since: datetime | None = None, until: datetime | None = None) -> list[Path]:
    """The event files that can hold events in ``[since, until]``: day directories first, then files by name
    (a file not written since ``since`` has nothing newer)."""
    return [f.path for f in org.runtime.event_reader.files(since, until)]


def timed_events(org: Org, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, dict]]:
    """Events in ``[since, until]`` as (time, event), merged over all process files in time order (a heap merge:
    every file is time-ordered by its single writer)."""
    return org.runtime.event_reader.timed(since, until)


def iter_events(org: Org, since: datetime | None = None, until: datetime | None = None) -> Iterator[dict]:
    return org.runtime.event_reader.events(since, until)


def events_view(org: Org, since=None, until=None, agent: str | None = None, kind: str | None = None,
                trace: str | None = None, errors: bool = False, limit: int | None = None,
                now: datetime | None = None) -> dict:
    """The merged raw stream, filtered by time window first, then by fields (``EventQueries.events_view``)."""
    return _wired.event_queries_of(org.runtime).events_view(since, until, agent, kind, trace, errors, limit, now)


def events(org: Org, since=None, until=None, agent=None, kind=None, trace=None, errors=False, limit=None,
           now: datetime | None = None) -> list[dict]:
    """The matching events (the last ``limit`` of them), oldest first."""
    return _wired.event_queries_of(org.runtime).events(since, until, agent, kind, trace, errors, limit, now)


class Follower(EventFollower):
    """Tails the event files: ``poll()`` returns the complete new lines of all files (today's and yesterday's day
    directories) since the last call, in time order. Files that appear later (a new process) are read from the start.
    The tailing is ``eventlog``'s; this keeps the old signature and takes the time from the clock of the runtime."""

    def __init__(self, org: Org, match: Callable[[dict], bool] | None = None, now: datetime | None = None):
        self.org, self.match = org, match or (lambda ev: True)
        self._follower = org.runtime.event_followers.follow(self.match, now or org.runtime.clock.now())

    def poll(self, emit: bool = True, now: datetime | None = None) -> list[dict]:
        return self._follower.poll(emit, now or self.org.runtime.clock.now())


def follow_events(org: Org, agent=None, kind=None, trace=None, errors=False, poll: float = 0.5,
                  sleep: Callable[[float], None] = time.sleep, max_polls: int | None = None) -> Iterator[dict]:
    """Yield new matching events as they are written (polling). Stops after ``max_polls`` polls if given."""
    return _wired.event_queries_sleeping(org.runtime, sleep).follow(agent, kind, trace, errors, poll, max_polls)


# ============================================================================================ message files


FileRec = MessageFile  # a message file as the index of the mail package sees it (data)
Msg = _wired.Msg
build_messages = _wired.build_messages


def scan_messages(org: Org) -> list[FileRec]:
    """Every message file of every mailbox of root and the live agents, parsed once (cached by path + mtime)."""
    return org.runtime.message_index.scan()


def Traces(org: Org, msgs: dict, batches: dict[str, list[str]] | None = None):  # noqa: N802 - it was the class of the trace of every message
    """The trace of every message (``MessageTraceDeriver``): ``.of(message id)`` is ``(trace id or None, source)``."""
    return _wired.trace_derivers_of(org.runtime).derive(msgs, batches)


# ============================================================================================ runs


def _running_ledger(org: Org) -> dict[str, dict]:
    return org.runtime.run_registry.all()


RunRec = _wired.RunRec
run_events = _wired.run_events


def _run_logs(org: Org, agent: str) -> list[tuple[str, Path]]:
    return [(f.stem, f.path) for f in org.runtime.run_log_reader.files(agent)]


def collect_runs(org: Org, since: datetime | None, until: datetime | None, evs: dict[str, dict[str, dict]] | None = None,
                 agents: list[str] | None = None) -> list[RunRec]:
    """Every run that STARTED in ``[since, until]``: the run logs of the live agents (the file truth: one log = one
    run = one run of budget), completed with ``run.start/run.end`` events where there are some, plus runs known only
    from events (agents retired since). Oldest first."""
    return _wired.run_collection_of(org.runtime).collect(since, until, evs, agents)


# ============================================================================================ trace


def run_window(org: Org, task: Msg, result: Msg | None, root_tasks: list[Msg]) -> tuple[str, str | None]:
    """(start, end) of a root task's run window, as 21-character timestamps, exactly as ``progress`` counts runs."""
    return _wired.run_window(task, result, root_tasks)


def trace(org: Org, task_id: str, now: datetime | None = None) -> dict:
    """One request as a tree, in time order, with totals (``TraceQueries.trace``)."""
    return _wired.trace_queries_of(org.runtime).trace(task_id, now)


# ============================================================================================ metrics


def metrics(org: Org, since="24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> dict:
    """Counts, rates and percentiles over ``[since, now]`` (``MetricQueries.metrics``)."""
    return _wired.metric_queries_of(org.runtime).metrics(since, by, now, agent)


# ============================================================================================ the text of events, traces and metrics (C-obs-2)


def render_events(view: dict, max_lines: int | None = None) -> str:
    evs = view["events"]
    if not evs:
        return "(no matching events)" + ("" if view.get("any", True) else " - this organization has no event files yet")
    lines = [format_event(ev) for ev in evs]
    head = f"{view['shown']} of {view['total']} matching event(s), oldest first"
    if view["total"] > view["shown"]:
        head += f" - {view['total'] - view['shown']} earlier one(s) not shown: narrow with since/agent/kind/trace or raise the limit"
    return "\n".join([head, *_cap(lines, max_lines, "since/agent/kind/trace")])


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
    return wire_eventlog.system_reader().tail(event_file(path), nbytes)


def _scheduler_files(org: Org) -> list[tuple[int, int, Path]]:
    """(start_epoch_ms, pid, path) of every scheduler event file, newest process first."""
    out = [(f.start_ms, f.pid, f.path) for f in org.runtime.event_reader.files() if f.proc == "scheduler"]
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
    return wire_eventlog.system_reader().head(event_file(path))


def now_view(org: Org, now: datetime | None = None) -> dict:
    """What is happening right now. Works with no events (then the event-derived parts are empty)."""
    from .progress import _human_items

    now = _aware(now) or org.runtime.clock.now()
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
                meta, err, _ = org.runtime.resources.meta_cache.read(d / n)
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
    reader = org.runtime.event_reader
    for f in reader.files(now - timedelta(days=2), None)[-3:]:
        for ev in reader.tail(f, 8192)[-1:]:
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


def _check_budget(org: Org, files: list[FileRec], now: float) -> dict:
    """Budget conservation.

    Budget is derived from messages and run logs (``Org.budget`` = received - handed down - run logs). Runs of budget
    enter only from root (a task's or a note's ``budget`` in root's ``sent/``); they leave in four ways, and nothing
    else: held by an agent now (the sum of ``Org.budget``), consumed (run logs of live agents, and of retired
    agents, see ``RetiredArchive.run_count``), returned to root (the ``budget`` of messages root received: results and
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
    archive = org.runtime.retired_archive
    used_retired = archive.run_count()
    dropped = sum(archive.unspent_budget(tree) for tree in archive.trees() if tree.top_level)
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
    reader = org.runtime.event_reader
    files = reader.files()
    for f in sorted(files, key=lambda x: (x.day, x.path.name)):
        expect = 1
        for _, ev in reader.read_file(f):
            seq = ev.get("seq")
            if not isinstance(seq, int) or isinstance(seq, bool):
                continue
            if seq != expect:
                where = f"{f.day}/{f.path.name}"
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
    at = (_aware(now) or org.runtime.clock.now()).timestamp()
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
