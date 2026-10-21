"""``MailAgentOverviews``: the overview of an agent (or of root) as titled sections of lines."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from ..agents import CharterReader
from ..attention import section
from ..kernel import ROOT, JsonObject, Message, clip_line, fmt_dur
from ..mail import MailboxReader
from ._data import AgentRow, Section, Snapshot
from ._ports import AgentOverviews, AgentWork, ReadableEvents
from .api import RequestQuery


class MailAgentOverviews(AgentOverviews):
    def __init__(self, charters: CharterReader, work: AgentWork, mailbox: MailboxReader, events: ReadableEvents, requests: RequestQuery) -> None:
        self._charters = charters
        self._work = work
        self._mailbox = mailbox
        self._events = events
        self._requests = requests

    def overview(self, addr: str, row: AgentRow, snap: Snapshot, events: list[JsonObject]) -> list[Section]:
        if addr == ROOT:
            return self._root_overview(snap)
        doc: list[Section] = []
        meta, _ = self._charters.charter(addr)
        head = [f"state    {row.glyph} {row.word}", f"role     {row.role}", f"model    {row.model}",
                f"budget   {row.budget} run(s) left; {row.runs_used} run(s) used",
                f"mailbox  {row.unread} unread, {row.open_tasks} open task(s), {row.delegated} delegated and outstanding"]
        if row.parent:
            head.insert(1, f"parent   {row.parent}")
        if row.services:
            head.append("offers   " + ", ".join(row.services))
        if meta.get("tools"):
            head.append("tools    " + ", ".join(map(str, cast("Iterable[object]", meta["tools"]))))
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
        tasks = self._work.open_tasks(addr)
        doc.append(Section(f"Open tasks ({len(tasks)})", self._task_lines(tasks) or ["none"]))
        out = self._work.outstanding(addr)
        lines = []
        for t in out:
            target = snap.row(t.to)
            lines.append(f'"{t.title}" -> {t.to}  [{target.word if target else "gone"}]  budget {t.budget}')
        doc.append(Section(f"Delegated, outstanding ({len(out)})", lines or ["none"]))
        recent = self._events.lines(events[-8:], me=addr)
        doc.append(Section("Latest activity", [x.text for x in recent] or ["(no events for this agent)"],
                           frozenset(i for i, x in enumerate(recent) if x.error)))
        return doc

    def _task_lines(self, tasks: list[Message]) -> list[str]:
        lines: list[str] = []
        for t in tasks:
            lines.append(f'"{t.title}"  from {t.sender}  budget {t.budget}')
            crit = section(t.body, "acceptance criteria")
            for c in crit[:6]:
                lines.append(f"    · {clip_line(c.lstrip('-* '), 110)}")
            if len(crit) > 6:
                lines.append(f"    · … {len(crit) - 6} more")
        return lines

    def _current_run(self, addr: str, row: AgentRow) -> list[str]:
        batch = self._mailbox.messages(addr, "inflight")
        lines = [f"elapsed {fmt_dur((row.elapsed_s or 0) * 1000)}"]
        lines.append(f"batch of {len(batch)} message(s):")
        for m in batch:
            lines.append(f'  {m.type} "{m.title or m.id}" from {m.sender}' + (f"  [{m.status}]" if m.status else ""))
        if row.queued_behind:
            lines.append(f"{row.queued_behind} more message(s) wait for the next run")
        return lines

    def _root_overview(self, snap: Snapshot) -> list[Section]:
        doc = [Section("You (root)", [f"{len(snap.agents) - 1} agent(s); {snap.running} running, {snap.queued} queued"
                                       + (f"; {snap.retired} retired" if snap.retired else ""),
                                       snap.scheduler.text])]
        doc.append(Section(f"Needs you ({len(snap.needs_you)})", [line for _, line in snap.needs_you] or ["nothing"]))
        reqs = self._requests.requests(snap)
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
