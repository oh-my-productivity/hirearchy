"""The cases of a service, derived from the mailboxes of its owner and its client and from the run logs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..agents import AgentDirectory
from ..kernel import ROOT, Message, latest_results, link_ids, msg_time, parent, verdict_tier
from ..mail import MailboxReader
from ..services import ServiceCatalog
from ._ports import FeedbackWords, PlaybookTimelines, RunCounter
from .api import Case, CaseHistory, Verdict, lessons_of, version_at


def _within(stamp: str, bounds: tuple[str, str | None]) -> bool:
    """Is ``stamp`` in the interval of a task: from its send up to its successor's send (exclusive), or to the window's end for the last one?"""
    return bounds[0] <= stamp and (bounds[1] is None or stamp < bounds[1])


@dataclass(frozen=True)
class _Spend:
    """The numbers of a case that split the user's requests from root's relayed reworks (design 4.2, 4.3)."""

    relayed_runs: int
    relayed_returned: int
    relayed_overlap: int
    unsplit_runs: int
    user_granted: int
    user_ceiling: int


def _spend(
    tasks: list[Message], results: Mapping[str, Message], sent: Sequence[Message], team: Sequence[str], human: bool, start: str, end: str | None,
    charged: Sequence[str],
) -> _Spend:
    """The relayed and user numbers of the chain ``tasks``, from the client's ``sent`` box, the latest ``results`` it received, the stamps of the
    charged runs ``charged`` in the case window (``start`` to ``end``, inclusive) and whether the client is ``human`` (root)."""
    bounds = [(t.id[:21], tasks[k + 1].id[:21] if k + 1 < len(tasks) else None) for k, t in enumerate(tasks)]
    relayed = [b for t, b in zip(tasks, bounds) if t.source == "relayed"]

    def in_relayed(s: str) -> bool:
        return any(_within(s, b) for b in relayed)

    handed_down = [m for m in sent if m.type == "note" and m.budget > 0 and m.to in team and m.id[:21] >= start and (end is None or m.id[:21] <= end)]
    grants = sorted((m for m in handed_down if human and not in_relayed(m.id[:21])), key=lambda m: m.id)  # the user grants
    users = [t for t in tasks if t.source != "relayed"]
    ceiling = 0
    for h in sorted([*users, *grants], key=lambda m: m.id) if human else []:  # the hand-downs, oldest first
        runs = sum(1 for s in charged if s < h.id[:21] and not in_relayed(s))
        handed = sum(t.budget for t in users if t.id < h.id) + sum(g.budget for g in grants if g.id < h.id)
        back = sum(min(r.budget, t.budget) for t in users if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
        ceiling = max(ceiling, runs + max(0, handed - runs - back) + h.budget)
    overlap, overlapped = 0, []
    for k, t in enumerate(tasks[:-1]):  # relayed runs that can lie in a later user interval
        r = results.get(t.id)
        if t.source != "relayed" or not any(u.source != "relayed" for u in tasks[k + 1:]) or (r is not None and r.id < tasks[k + 1].id):
            continue  # not relayed, no user task after it, or answered before its successor
        funds = t.budget + sum(n.budget for n in handed_down if _within(n.id[:21], bounds[k]))
        ran = sum(1 for s in charged if _within(s, bounds[k]))
        term = max(0, funds - (min(r.budget, t.budget) if r is not None else 0) - ran)
        overlap += term
        if term > 0:
            overlapped.append(k)
    unsplit = 0
    if overlapped:  # the runs of the user intervals after the first overlapped relayed task: counted with the user's, not apart
        later = [bounds[j] for j in range(overlapped[0] + 1, len(tasks)) if tasks[j].source != "relayed"]
        unsplit = sum(1 for s in charged if any(_within(s, b) for b in later))
    return _Spend(
        relayed_runs=sum(1 for s in charged if in_relayed(s)),
        relayed_returned=sum(min(r.budget, t.budget) for t in tasks if t.source == "relayed" and (r := results.get(t.id)) is not None),
        relayed_overlap=overlap, unsplit_runs=unsplit, user_granted=sum(g.budget for g in grants), user_ceiling=ceiling,
    )


class DerivedCaseHistory(CaseHistory):
    """Reads a service's requests from what its client sent, their results from what the client received, and the client's verdicts from the
    notes it sent; nothing is kept."""

    def __init__(
        self, catalog: ServiceCatalog, agents: AgentDirectory, mail: MailboxReader, words: FeedbackWords, timelines: PlaybookTimelines,
        counter: RunCounter,
    ) -> None:
        self._catalog = catalog
        self._agents = agents
        self._mail = mail
        self._words = words
        self._timelines = timelines
        self._counter = counter

    def playbook_timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        return self._timelines.timeline(owner, service)

    def cases(self, owner: str, service: str) -> list[Case]:
        contract = self._catalog.read_contract(owner, service)
        client = parent(owner)
        if contract is None or client is None:
            return []
        sent = self._mail.sent(client)
        since = contract.created
        mine = sorted(
            (m for m in sent if m.type == "task" and m.to == owner and m.service == service
             and (since is None or (msg_time(m) or since) >= since)),
            key=lambda m: m.id,
        )
        by_id = {m.id: m for m in mine}

        def head(m: Message) -> str:
            seen = {m.id}
            while m.revises in by_id and m.revises not in seen:
                m = by_id[m.revises]
                seen.add(m.id)
            return m.id

        chains: dict[str, list[Message]] = {}
        for m in mine:
            chains.setdefault(head(m), []).append(m)
        results = latest_results(self._mail.received(client))
        notes = sorted((m for m in sent if m.type == "note" and m.feedback and m.reply_to in by_id), key=lambda m: m.id)
        by_note = {n.id: n for n in notes}
        link_notes = sorted(
            (m for m in sent if m.type == "note" and not m.feedback and link_ids(m) and m.reply_to in by_note), key=lambda m: m.id,
        )
        kind = "human" if client == ROOT else "agent"
        others = sorted(m.id for m in sent if m.type == "task" and m.to == owner)
        team = self._agents.subtree(owner)
        timeline = self.playbook_timeline(owner, service)
        out = []
        for first, tasks in chains.items():
            ids = {t.id for t in tasks}
            last = tasks[-1]
            res = results.get(last.id)
            state = res.status if res is not None and res.status in ("done", "failed", "blocked") else "open"
            final = res is not None and res.status in ("done", "failed")
            end = res.id[:21] if res is not None and final else None
            later = next((i for i in others if i > last.id and i not in ids), None)
            if later and (end is None or later[:21] < end):
                end = later[:21]
            start = tasks[0].id[:21]
            charged = [s for s, credited in self._counter.stamps(team, start, end) if not credited]
            spend = _spend(tasks, results, sent, team, kind == "human", start, end, charged)
            step = {t.id: i for i, t in enumerate(tasks)}
            verdicts = [
                self._verdict(n, step[n.reply_to], [m for m in link_notes if m.reply_to == n.id]) for n in notes if n.reply_to in ids
            ]
            out.append(Case(
                id=first, service=service, owner=owner, tasks=tasks, result=res, state=state,
                playbook=tasks[0].playbook or 0,
                used=version_at(timeline, msg_time(first_result) if (first_result := results.get(tasks[0].id)) else None),
                reworks=len(tasks) - 1, budget=sum(t.budget for t in tasks),
                runs=len(charged), relayed_runs=spend.relayed_runs,
                lessons=[x for t in tasks if (r := results.get(t.id)) is not None and (x := lessons_of(r))],
                lesson_ids=[r.id for t in tasks if (r := results.get(t.id)) is not None and lessons_of(r)],
                lesson_sources=[t.source or "" for t in tasks if (r := results.get(t.id)) is not None and lessons_of(r)],
                verdicts=verdicts, started=msg_time(tasks[0]),
                finished=msg_time(res) if res is not None and final else None,
                client_kind=kind, relayed_reworks=sum(t.source == "relayed" for t in tasks[1:]),
                returned=sum(min(r.budget, t.budget) for t in tasks if (r := results.get(t.id)) is not None),
                relayed_returned=spend.relayed_returned, relayed_overlap=spend.relayed_overlap, unsplit_runs=spend.unsplit_runs,
                user_granted=spend.user_granted, user_ceiling=spend.user_ceiling,
            ))
        return out

    def _verdict(self, note: Message, step: int, links: list[Message]) -> Verdict:
        """The verdict a feedback note is. Its link is the latest human-tier candidate, else the latest candidate of any tier. A candidate is the
        note's own criterion, always of the relayed tier (the assistant wrote it, whatever the note's source), or a link note that replies to it,
        which is human only when root sent it with ``source="human"`` after the user's yes. ``confirmed`` collects the criteria of every
        human-tier link note."""
        candidates = sorted((m for m in (note, *links) if link_ids(m)), key=lambda m: m.id)

        def tier(m: Message) -> str:
            return "relayed" if m is note else verdict_tier(m)

        winning = [m for m in candidates if tier(m) == "human"] or candidates
        confirmed = dict.fromkeys(x for m in candidates if m is not note and tier(m) == "human" for x in link_ids(m) if x.startswith("C"))
        return Verdict(
            note.feedback or "", self._words.feedback_text(note), msg_time(note), note.reply_to or "", step, note, tier=verdict_tier(note),
            links=link_ids(winning[-1]) if winning else (), links_tier=tier(winning[-1]) if winning else "", confirmed=tuple(confirmed),
            link_notes=tuple(sorted(links, key=lambda m: m.id)),
        )

    def case_of(self, task: Message) -> Case | None:
        if not task.service or not self._agents.exists(task.to):
            return None
        return next((c for c in self.cases(task.to, task.service) if task.id in {t.id for t in c.tasks}), None)
