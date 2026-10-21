"""The runs of the views: one record per run log, completed with the events of the run."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from ..agents import AgentDirectory
from ..eventlog import EventReader
from ..kernel import JsonObject, clip_line, parse_time, stamp_of
from ..mail import MailboxReader
from ..runs import RunLogReader, RunRegistry
from ._ports import RunCollection
from ._util import ms_between, plain


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
    """The record of a run as the views show it: every field but the log, times as ISO text."""
    return cast(JsonObject, plain({k: v for k, v in run.__dict__.items() if k != "log"}))


def run_events(evs: Iterable[JsonObject | tuple[datetime, JsonObject]]) -> dict[str, dict[str, JsonObject]]:
    """run id -> {"start": run.start, "end": run.end, "orphan": run.orphan} from an iterable of events or (t, event)."""
    out: dict[str, dict[str, JsonObject]] = defaultdict(dict)
    for item in evs:
        ev = item[1] if isinstance(item, tuple) else item
        kind = ev.get("kind")
        if kind in ("run.start", "run.end", "run.orphan") and ev.get("run"):
            out[str(ev["run"])][str(kind).split(".")[1]] = ev
    return out


def _queue_ms(start: datetime, batch: list[str] | None) -> float | None:
    stamps = [t for b in batch or () if (t := stamp_of(str(b)))]
    return max(0.0, ms_between(min(stamps), start)) if stamps else None


def _make_run(reader: RunLogReader, agent: str, log: Path | None, stem: str, start: datetime, ev: Mapping[str, JsonObject],
              running_stem: str | None, is_live: bool) -> RunRec:
    run = RunRec(agent=agent, run=f"{agent}@{stem}", start=start, log=log)
    s, e, o = ev.get("start"), ev.get("end"), ev.get("orphan")
    if s:
        run.source = "events"
        run.batch = [str(b) for b in cast("list[object]", s.get("batch") or [])]
        run.traces = [str(t) for t in cast("list[object]", s.get("traces") or [])]
        # the envelope ``pid`` is the EMITTER's (the scheduler); the kiro process is ``child_pid`` (its group: ``pgid``)
        child = s.get("child_pid") if isinstance(s.get("child_pid"), int) else s.get("pgid")
        run.pid = child if isinstance(child, int) and not isinstance(child, bool) else None
        st = parse_time(s.get("ts"))
        run.queue_ms = _queue_ms(st or start, run.batch)
    if e:
        run.source = "events"
        run.ok = bool(e.get("ok"))
        exit_code = e.get("exit_code")
        run.exit_code = exit_code if isinstance(exit_code, int) else None
        duration = e.get("duration_ms")
        run.duration_ms = float(duration) if isinstance(duration, (int, float)) else None
        run.error = clip_line(e["error"], 500) if e.get("error") else None
        run.end = parse_time(e.get("ts"))
        run.outcome = ("timeout" if e.get("timed_out") else "killed" if e.get("killed")
                       else "ok" if run.ok else "failed")
    elif o:
        run.outcome, run.ok = "killed", False
        run.error = clip_line(f"orphan: {o.get('action')} {o.get('detail') or ''}", 200)
    elif log is not None:
        facts = reader.facts(log)
        if facts.get("timed_out"):
            run.outcome, run.ok = "timeout", False
        elif facts.get("killed"):
            run.outcome, run.ok = "killed", False
        elif facts.get("failed_start"):
            run.outcome, run.ok = "failed", False
        elif "exit_code" in facts:
            code = cast(int, facts["exit_code"])
            run.exit_code = code
            run.ok = code == 0
            run.outcome = "ok" if run.ok else "failed"
        if "seconds" in facts:
            run.duration_ms = cast(int, facts["seconds"]) * 1000.0
        if run.outcome == "unknown" and is_live and running_stem == stem:
            run.outcome = "running"
    if run.outcome == "unknown" and is_live and running_stem == stem:
        run.outcome = "running"
    return run


class RunCollector(RunCollection):
    """Every run is one run log (the file truth: one log = one run = one run of budget), completed with ``run.start`` / ``run.end`` events where
    there are some; runs known only from events (their agents were retired since) are added."""

    def __init__(self, logs: RunLogReader, registry: RunRegistry, agents: AgentDirectory, mailbox: MailboxReader, events: EventReader) -> None:
        self._logs, self._registry, self._agents, self._mailbox, self._events = logs, registry, agents, mailbox, events

    def collect(
        self, since: datetime | None, until: datetime | None, events: Mapping[str, Mapping[str, JsonObject]] | None = None,
        agents: Sequence[str] | None = None,
    ) -> list[RunRec]:
        evs = events if events is not None else run_events(self._events.timed(since, None))
        running = self._registry.all()
        live = {a for a in self._agents.agents() if self._mailbox.has_inflight(a)}
        out: list[RunRec] = []
        seen: set[str] = set()
        for agent in agents if agents is not None else self._agents.agents():
            rec = running.get(agent)
            running_stem = Path(str(rec.get("log", ""))).stem if rec else None
            logs = self._logs.files(agent)
            for log in logs:
                stem = log.stem
                start = stamp_of(stem)
                if start is None or (since and start < since) or (until and start > until):
                    continue
                rid = f"{agent}@{stem}"
                seen.add(rid)
                latest = stem == logs[-1].stem
                out.append(_make_run(self._logs, agent, log.path, stem, start, evs.get(rid, {}), running_stem or (stem if latest else None), agent in live))
        if agents is None:  # runs of agents that no longer exist: only the events know them
            for rid, ev in evs.items():
                s = ev.get("start")
                if rid in seen or not s or "@" not in rid:
                    continue
                agent, _, stem = rid.rpartition("@")
                start = stamp_of(stem) or parse_time(s.get("ts"))
                if start is None or (since and start < since) or (until and start > until) or self._agents.exists(agent):
                    continue
                out.append(_make_run(self._logs, agent, None, stem, start, ev, None, False))
        return sorted(out, key=lambda r: (r.start, r.run))

    def team_runs(
        self, team: Sequence[str], in_windows: Callable[[str], bool], events: Mapping[str, Mapping[str, JsonObject]]
    ) -> list[RunRec]:
        runs: list[RunRec] = []
        running = self._registry.all()
        for agent in team:
            rec = running.get(agent)
            running_stem = Path(str(rec.get("log", ""))).stem if rec else None
            logs = self._logs.files(agent)
            for log in logs:
                stem = log.stem
                if not in_windows(stem):
                    continue
                start = stamp_of(stem)
                if start is None:
                    continue
                runs.append(_make_run(self._logs, agent, log.path, stem, start, events.get(f"{agent}@{stem}", {}),
                                      running_stem or (stem if stem == logs[-1].stem else None), self._mailbox.has_inflight(agent)))
        runs.sort(key=lambda r: (r.start, r.run))
        return runs
