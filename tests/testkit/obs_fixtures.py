"""Synthetic observability data for tests: a controllable clock and writers for event files exactly per the spec
(``.runtime/events/<YYYY-MM-DD>/<proc>-<pid>-<start_epoch_ms>.jsonl``, one JSON object per line, per-process ``seq``).

The query layer must never import the emitting module, so tests build the files by hand with these helpers.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from orgmcp.core import ROOT, Message, Org, join_frontmatter, split_frontmatter

from .clocks import clock_ports

T0 = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone.utc)


class Clock:
    """A callable serving ``Clock.now`` of the runtimes (``freeze``): time only moves when the test says so (plus 1 microsecond per
    call, so ids stay unique and ordered)."""

    def __init__(self, start: datetime = T0):
        self.t = start

    def __call__(self) -> datetime:
        self.t += timedelta(microseconds=1)
        return self.t

    def at(self, offset_s: float) -> datetime:
        """Jump to ``T0 + offset_s`` seconds (never backwards)."""
        target = T0 + timedelta(seconds=offset_s)
        if target > self.t:
            self.t = target
        return self.t


def freeze(process_overrides) -> Clock:
    """The controllable clock, as the ``Clock`` of every runtime opened from now on (``process_overrides``: the fixture of tests/testkit/fixtures.py)."""
    clock = Clock()
    process_overrides(clock_ports(clock))
    return clock


def stamp(offset_s: float) -> datetime:
    return T0 + timedelta(seconds=offset_s)


class EventLog:
    """Writes event lines the way the runtime does: one file per (proc, pid) per UTC day, append-only, ``seq`` counting
    the lines of ONE file (it restarts at 1 in each day's file)."""

    def __init__(self, org: Org):
        self.org = org
        self.seq: dict[Path, int] = {}
        self.started: dict[tuple[str, int], int] = {}
        self.mtimes: dict[Path, float] = {}

    def path(self, proc: str, pid: int, day: str) -> Path:
        key = (proc, pid)
        start_ms = self.started.setdefault(key, int(T0.timestamp() * 1000) + len(self.started))
        return self.org.root / ".runtime" / "events" / day / f"{proc}-{pid}-{start_ms}.jsonl"

    def emit(self, kind: str, ts: datetime, *, proc: str = "mcp", pid: int = 4242, actor: str = "runtime",
             run: str | None = None, trace: str | None = None, skip_seq: int = 0, **fields) -> dict:
        p = self.path(proc, pid, ts.strftime("%Y-%m-%d"))
        self.seq[p] = self.seq.get(p, 0) + 1 + skip_seq
        ev = {"v": 1, "ts": ts.isoformat(), "seq": self.seq[p], "proc": proc, "pid": pid, "kind": kind,
              "actor": actor, "run": run, "trace": trace, **fields}
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev) + "\n")
        mtime = self.mtimes[p] = max(self.mtimes.get(p, 0.0), ts.timestamp())  # the file was last written at its last event
        os.utime(p, (mtime, mtime))
        return ev

    # ---- the common shapes
    def run(self, agent: str, stem: str, start: datetime, seconds: float, batch: list[str], traces: list[str],
            ok: bool = True, timed_out: bool = False, killed: bool = False, error: str | None = None, pid: int = 7000) -> str:
        """run.start + run.end of one run whose log stem is ``stem``; returns the run id."""
        rid = f"{agent}@{stem}"
        self.emit("run.start", start + timedelta(milliseconds=5), proc="scheduler", pid=pid, run=rid, agent=agent,
                  batch=batch, traces=traces, pgid=1, model=None, budget_before=3)
        self.emit("run.end", start + timedelta(seconds=seconds), proc="scheduler", pid=pid, run=rid, agent=agent,
                  ok=ok, exit_code=0 if ok else (-9 if killed or timed_out else 1), duration_ms=int(seconds * 1000),
                  timed_out=timed_out, killed=killed, budget_after=2, error=error)
        return rid

    def tool(self, ts: datetime, actor: str, tool: str, *, ok: bool = True, ms: int = 5, error: str | None = None,
             run: str | None = None, trace: str | None = None, args: dict | None = None, proc: str = "mcp", pid: int = 4242) -> dict:
        return self.emit("tool.call", ts, proc=proc, pid=pid, actor=actor, run=run, trace=trace, tool=tool, ok=ok, ms=ms,
                         error=error, error_type=None if ok else "OrgError", args=args or {})

    def partial_line(self, proc: str, pid: int, day: str, text: str = '{"v": 1, "ts": "2026-10-18T10:0') -> None:
        p = self.path(proc, pid, day)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(text)


def stamp_trace(org: Org, trace_id: str, *message_ids: str) -> None:
    """Add ``trace: <id>`` to the frontmatter of every copy of the given messages (what the runtime does at send time)."""
    wanted = set(message_ids)
    for a in (ROOT, *org.agents()):
        for box in ("inbox", "inflight", "read", "sent"):
            d = org.dir(a) / box
            if not d.is_dir():
                continue
            for p in d.glob("*.md"):
                if p.stem in wanted:
                    meta, body = split_frontmatter(p.read_text(encoding="utf-8"))
                    meta["trace"] = trace_id
                    p.write_text(join_frontmatter(meta, body), encoding="utf-8")


def strip_trace(org: Org) -> None:
    """Remove the ``trace`` frontmatter field from every message (an org created before traces existed)."""
    for a in (ROOT, *org.agents()):
        for box in ("inbox", "inflight", "read", "sent"):
            d = org.dir(a) / box
            if not d.is_dir():
                continue
            for p in d.glob("*.md"):
                meta, body = split_frontmatter(p.read_text(encoding="utf-8"))
                if meta.pop("trace", None) is not None:
                    p.write_text(join_frontmatter(meta, body), encoding="utf-8")


def run_ids(org: Org, agent: str) -> list[str]:
    d = org.dir(agent) / "runs"
    return [f"{agent}@{p.stem}" for p in sorted(d.glob("*.log"))] if d.is_dir() else []


class Story:
    """A finished request on a ``root -> ceo -> ceo/eng`` org with a controlled clock, matching run logs and events.

    t=0 root tasks ceo; t=3 ceo runs (delegates to eng, one refused attempt); t=70 eng runs (writes, reports); t=115 ceo
    runs again (reports done, returns budget). ``record`` stamps ``trace`` on the messages (as the runtime does).
    """

    def __init__(self, org: Org, clock: Clock, events: bool = True, record: bool = True):
        self.org, self.clock = org, clock
        self.log = EventLog(org) if events else None
        o = org
        clock.at(0)
        self.task = o.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
        tid = self.task.id
        self.ids = [tid]
        # --- run 1 of ceo: queue 3s, 40s long
        clock.at(3)
        batch = [m.id for m in o.begin_run("ceo")]
        log1 = o.start_run_log("ceo")
        self.run1 = f"ceo@{log1.stem}"
        clock.at(20)
        self.sub = o.delegate("ceo", "ceo/eng", "Build", "Build it", "Built", budget=3)
        self.ids.append(self.sub.id)
        clock.at(45)
        o.end_run("ceo", True)
        log1.write_text("# exit 0 after 42s\n")
        # --- run 2: eng, queue 50s (delegated at 20, run at 70), 30s long
        clock.at(70)
        batch2 = [m.id for m in o.begin_run("ceo/eng")]
        log2 = o.start_run_log("ceo/eng")
        self.run2 = f"ceo/eng@{log2.stem}"
        clock.at(95)
        o.write("ceo/eng", "ceo/eng/work/out.md", "built")
        self.res_eng = o.report("ceo/eng", self.sub.id, "done", "Built.", ["ceo/eng/work/out.md"])
        self.ids.append(self.res_eng.id)
        clock.at(100)
        o.end_run("ceo/eng", True)
        log2.write_text("# exit 0 after 30s\n")
        # --- run 3: ceo again
        clock.at(115)
        batch3 = [m.id for m in o.begin_run("ceo")]
        log3 = o.start_run_log("ceo")
        self.run3 = f"ceo@{log3.stem}"
        clock.at(125)
        o.write("ceo", "ceo/work/out.md", "all done")
        self.res = o.report("ceo", tid, "done", "Shipped.", ["ceo/work/out.md"])
        self.ids.append(self.res.id)
        clock.at(130)
        o.end_run("ceo", True)
        log3.write_text("# exit 0 after 15s\n")
        if record:
            stamp_trace(o, tid, *self.ids)
        else:
            strip_trace(o)  # the runtime stamps at send time; an old org has no such field
        if self.log:
            self._events(tid, batch, batch2, batch3)

    def _events(self, tid, b1, b2, b3):
        e, tid_ = self.log, self.task.id
        s = stamp
        e.emit("scheduler.start", s(0), proc="scheduler", pid=7000, mode="until_done", max_runs=None, max_parallel=3, version="x")
        e.run("ceo", self.run1.split("@")[1], s(3), 42, b1, [tid_])
        e.tool(s(5), "ceo", "inbox", run=self.run1, trace=None)
        e.tool(s(10), "ceo", "delegate", ok=False, ms=3, run=self.run1, trace=tid_,
               error="not enough budget: you have 5 run(s) and must keep 2 in reserve", args={"to": "ceo/eng", "budget": 9})
        e.tool(s(20), "ceo", "delegate", run=self.run1, trace=tid_, args={"to": "ceo/eng", "title": "Build", "budget": 3})
        e.run("ceo/eng", self.run2.split("@")[1], s(70), 30, b2, [tid_])
        e.tool(s(90), "ceo/eng", "write", run=self.run2, trace=tid_, args={"path": "ceo/eng/work/out.md", "content_chars": 5})
        e.tool(s(95), "ceo/eng", "report", run=self.run2, trace=tid_, args={"task_id": self.sub.id, "status": "done"})
        e.run("ceo", self.run3.split("@")[1], s(115), 15, b3, [tid_])
        e.tool(s(125), "ceo", "report", run=self.run3, trace=tid_, args={"task_id": tid_, "status": "done"})
        e.emit("scheduler.exit", s(131), proc="scheduler", pid=7000, reason="finished: no open tasks", runs_started=3)
        e.tool(s(0.0005), ROOT, "delegate", trace=tid_, proc="cli", pid=5100, args={"to": "ceo", "title": "Ship it", "budget": 6})


def message(org: Org, sender: str, to: str, **kw) -> Message:
    return org.send(sender, to, kw.pop("body", "hello"), **kw)
