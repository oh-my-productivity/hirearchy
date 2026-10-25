"""``MailEscapeCounter``: the client's rejections of what a team signed off, and what the FAILs before them cost (design 5.5, 10).

What a delivery is, who signed it off and why an escape happened is ``SignedDeliveries``' (``reflection``'s rules, converted in ``app``); this counts."""

from __future__ import annotations

from collections import Counter

from ..agents import AgentDirectory
from ..kernel import ROOT, latest_results, msg_time, parent
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._ports import ClientRework, EscapeCounter, EscapeCounts, SignedDeliveries


NOT_ITS = ("contract-gap", "relayed-error", "relayed-carry-over")  # the escapes that are not the verifier's, in the order the report lists them


class MailEscapeCounter(EscapeCounter):
    def __init__(
        self, agents: AgentDirectory, mail: MailboxReader, runs: RunLogReader, rework: ClientRework, deliveries: SignedDeliveries,
    ) -> None:
        self._agents = agents
        self._mail = mail
        self._runs = runs
        self._rework = rework
        self._signed = deliveries

    def counts(self, addr: str) -> EscapeCounts:
        own = self._signed.deliveries(addr)
        deliveries, unknown = list(own.items), [own.unknown]
        boss = parent(addr)
        rechecks = rework_runs = 0
        if boss is not None and boss != ROOT:  # root is nobody's owner: its direct reports have only their own deliveries
            theirs = self._signed.deliveries(boss)
            deliveries += [d for d in theirs.items if d.signer == addr and d.signer != boss]
            unknown.append(theirs.unknown)
            rechecks, rework_runs = self._rechecks(addr, boss)
        judged = [d for d in deliveries if d.judged]
        escapes = [d for d in judged if d.escape]
        not_its = Counter(d.cause for d in escapes if not d.counted)
        listed = [*(c for c in NOT_ITS if c in not_its), *(c for c in not_its if c not in NOT_ITS)]
        return EscapeCounts(
            sum(d.counted for d in escapes), len(judged), rechecks, rework_runs, tuple((c, not_its[c]) for c in listed), "; ".join(u for u in unknown if u),
        )

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
