"""``CachedRequestQuery``: root's requests, and the progress line and the trace of one."""

from __future__ import annotations

import re
from datetime import datetime

from ..agents import AgentDirectory
from ..kernel import ROOT, OrgError, latest_results, stamp_of
from ..mail import MailboxReader
from ..observability import ObservabilityRenderer, TraceQueries
from ..progress import ProgressReporter
from ._const import REQUESTS_TTL
from ._data import RequestRow, Snapshot
from ._ports import RequestFacts, RequestSource, RequestTexts
from ._text import clean_text
from .api import DashboardState, RequestQuery, SnapshotQuery


class MailRequestRows(RequestSource):
    """One row per task root gave (the last 300), from the mailboxes of root and what ``progress`` says of each."""

    def __init__(self, mailbox: MailboxReader, agents: AgentDirectory, facts: RequestFacts) -> None:
        self._mailbox = mailbox
        self._agents = agents
        self._facts = facts

    def rows(self, snap: Snapshot) -> list[RequestRow]:
        now = snap.at
        tasks = [m for m in self._mailbox.sent(ROOT) if m.type == "task"]
        results = latest_results(self._mailbox.received(ROOT))
        waiting: dict[str, int] = {}
        for mid, _ in snap.needs_you:
            found = self._mailbox.find_anywhere(ROOT, mid)
            tr = found.trace if found else None
            if tr:
                waiting[tr] = waiting.get(tr, 0) + 1
        rows: list[RequestRow] = []
        for t in reversed(tasks[-300:]):
            res = results.get(t.id)
            try:
                team = [a for a in self._agents.subtree(t.to) if a != ROOT] if self._agents.exists(t.to) else []
                state, who = self._facts.state_of(t, res, team)
                runs_text = self._facts.runs_text(t, res, team)
                last = self._facts.last_activity(team)
            except Exception as exc:  # noqa: BLE001 - one odd request must not hide the others
                state, who, runs_text, last = f"? ({type(exc).__name__})", "", "runs ?", None
            m = re.match(r"runs (\d+) of (\d+)", runs_text)
            arts = self._facts.artifacts(res) if res is not None and res.status in ("done", "failed") else []
            rows.append(RequestRow(
                id=t.id, title=t.title, assignee=t.to, service=t.service, revises=t.revises, state=state,
                klass=re.split(r"[ :(]", state, 1)[0], who=who, runs_used=int(m.group(1)) if m else 0,
                runs_given=int(m.group(2)) if m else 0, runs_text=runs_text,
                last_activity_s=max(0.0, (now - last).total_seconds()) if last else None, created=stamp_of(t.id),
                needs_you=waiting.get(t.id, 0), artifacts=arts,
            ))
        return rows


class ProgressRequestTexts(RequestTexts):
    def __init__(self, reporter: ProgressReporter, traces: TraceQueries, renderer: ObservabilityRenderer) -> None:
        self._reporter = reporter
        self._traces = traces
        self._renderer = renderer

    def line(self, task_id: str, now: datetime) -> str:
        return self._reporter.progress(task_id, now).splitlines()[0]

    def trace(self, task_id: str, now: datetime) -> str:
        return clean_text(self._renderer.render_trace(self._traces.trace(task_id, now)))


class CachedRequestQuery(RequestQuery):
    def __init__(self, state: DashboardState, snapshots: SnapshotQuery, rows: RequestSource, texts: RequestTexts) -> None:
        self._state = state
        self._snapshots = snapshots
        self._rows = rows
        self._texts = texts

    def requests(self, snap: Snapshot | None = None) -> list[RequestRow]:
        self._state.refresh()
        snap = snap or self._state.snap or self._snapshots.snapshot()
        found = snap
        return self._state.memoised("requests", snap.sig + (len(snap.needs_you),), REQUESTS_TTL, lambda: self._rows.rows(found))

    def request_line(self, task_id: str) -> str:
        """The ``progress`` line of one request."""
        try:
            return self._texts.line(task_id, self._state.now())
        except Exception as exc:  # noqa: BLE001
            return f"(no progress line: {exc})"

    def trace_text(self, task_id: str) -> str:
        """The trace of one request (``TraceQueries`` rendered), or why there is none."""
        try:
            return self._texts.trace(task_id, self._state.now())
        except OrgError as exc:
            return f"no trace: {exc}"
        except Exception as exc:  # noqa: BLE001
            return f"the trace could not be computed: {type(exc).__name__}: {exc}"
