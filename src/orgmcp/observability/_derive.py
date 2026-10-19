"""The trace of every message, derived from the files."""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone

from ..kernel import ROOT, RUNTIME, stamp_of
from ..runs import RunLogReader
from ._messages import Msg
from ._ports import TraceDeriver, TraceDerivers

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class MessageTraceDeriver(TraceDeriver):
    """The trace of every message: as recorded in its frontmatter (``trace``), else derived from the files with the
    same rules the runtime applies at send time (spec section 3), best effort:

    1. root sends a task without ``revises``: its own id (``new``);
    2. ``reply_to`` / ``revises``: the trace of that message (``link``);
    3. the sender's open tasks at that moment (received, no final result yet) all share one trace (``open-task``);
    4. the sender's batch of that run (from ``run.start`` events, else the messages that arrived between its
       previous run and this one) has exactly one distinct trace (``batch``);
    5. otherwise unknown.
    """

    def __init__(self, msgs: Mapping[str, Msg], batches: Mapping[str, list[str]] | None, logs: RunLogReader) -> None:
        self.msgs, self.batches, self._logs = msgs, batches or {}, logs
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
            # the start of a run is read from the file name, ``.log`` included (21 characters of it): a stem shorter than a timestamp has none
            starts = [(t, f"{agent}@{f.stem}") for f in self._logs.files(agent) if (t := stamp_of(f.path.name))]
            self._starts[agent] = starts
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
        found = {t for b in batch if b != m.id and b in self.msgs if (t := self.of(b)[0]) is not None}
        return found


class LogTraceDerivers(TraceDerivers):
    """Makes a deriver over the run logs this one reads."""

    def __init__(self, logs: RunLogReader) -> None:
        self._logs = logs

    def derive(self, msgs: Mapping[str, Msg], batches: Mapping[str, list[str]] | None = None) -> TraceDeriver:
        return MessageTraceDeriver(msgs, batches, self._logs)
