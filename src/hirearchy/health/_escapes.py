"""``MailEscapeCounter``: the client's rejections of what a team signed off, and what the FAILs before them cost (design 5.5)."""

from __future__ import annotations

from collections import defaultdict
from typing import NamedTuple

from ..agents import AgentDirectory
from ..kernel import ROOT, Message, latest_results, msg_time, parent, verdict_tier
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._ports import ClientRework, EscapeCounter, EscapeCounts


class _Delivery(NamedTuple):
    signer: str  # the agent that signed it off: the last report to be done before the owner, else the owner
    judged: bool  # the human client gave a verdict after the owner's ``done``
    escape: bool  # one of those verdicts is a reject


class MailEscapeCounter(EscapeCounter):
    def __init__(self, agents: AgentDirectory, mail: MailboxReader, runs: RunLogReader, rework: ClientRework) -> None:
        self._agents = agents
        self._mail = mail
        self._runs = runs
        self._rework = rework

    def counts(self, addr: str) -> EscapeCounts:
        deliveries = self._deliveries(addr)
        boss = parent(addr)
        rechecks = rework_runs = 0
        if boss is not None and boss != ROOT:  # root is nobody's owner: its direct reports have only their own deliveries
            deliveries += [d for d in self._deliveries(boss) if d.signer == addr and d.signer != boss]
            rechecks, rework_runs = self._rechecks(addr, boss)
        return EscapeCounts(sum(d.escape for d in deliveries), sum(d.judged for d in deliveries), rechecks, rework_runs)

    def _deliveries(self, owner: str) -> list[_Delivery]:
        """The service deliveries of ``owner``: tasks of a service (not relayed reworks) whose latest result is ``done``."""
        received, sent = self._mail.received(owner), self._mail.sent(owner)
        results = latest_results(sent)
        sent_tasks = sorted(m.id for m in sent if m.type == "task")
        reports = set(self._agents.children(owner))
        done_by_reports = [m for m in received if m.type == "result" and m.status == "done" and m.sender in reports and m.reply_to]
        verdicts: dict[str, list[Message]] = defaultdict(list)
        for m in received:
            if m.type == "note" and m.feedback and m.reply_to:
                verdicts[m.reply_to].append(m)
        out = []
        for t in received:
            done = results.get(t.id)
            if t.type != "task" or not t.service or t.source == "relayed" or done is None or done.status != "done":
                continue
            later = {i for i in sent_tasks if i > t.id}
            signed = [r for r in done_by_reports if r.reply_to in later and r.id < done.id]
            signer = max(signed, key=lambda r: r.id).sender if signed else owner
            human = [v for v in verdicts[t.id] if v.id > done.id and verdict_tier(v) == "human"]
            out.append(_Delivery(signer, bool(human), any(v.feedback == "reject" for v in human)))
        return out

    def _rechecks(self, addr: str, boss: str) -> tuple[int, int]:
        """The re-checks of ``addr`` after a FAIL, and the runs of the authors that the FAILs cost (``boss`` is its parent)."""
        tasks = [m for m in self._mail.received(addr) if m.type == "task"]
        by_id = {t.id: t for t in tasks}
        results = latest_results(self._mail.sent(addr))
        driven = self._rework.driven(tasks, results)
        siblings = set(self._agents.children(boss)) - {addr}
        author_reworks = [m for m in self._mail.sent(boss) if m.type == "task" and m.revises and m.to in siblings]
        rechecks, runs = 0, set()
        for r in tasks:
            checked = by_id.get(r.revises or "")
            fail = results.get(checked.id) if checked else None
            if fail is None or fail.status != "done" or r.id in driven:
                continue
            window = [m for m in author_reworks if fail.id < m.id < r.id]
            if not window:
                continue
            rechecks += 1
            start, end = msg_time(fail), msg_time(r)
            if start is None or end is None:
                continue
            for author in {m.to for m in window}:
                runs |= {(author, w.start) for w in self._runs.windows(author) if start <= w.start < end}
        return rechecks, len(runs)
