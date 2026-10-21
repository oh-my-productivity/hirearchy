"""The cases of a service, derived from the mailboxes of its owner and its client and from the run logs."""

from __future__ import annotations

from datetime import datetime

from ..agents import AgentDirectory
from ..kernel import Message, latest_results, msg_time, parent
from ..mail import MailboxReader
from ..services import ServiceCatalog
from ._ports import FeedbackWords, PlaybookTimelines, RunCounter
from .api import Case, CaseHistory, Verdict, lessons_of, version_at


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
            step = {t.id: i for i, t in enumerate(tasks)}
            verdicts = [
                Verdict(n.feedback or "", self._words.feedback_text(n), msg_time(n), n.reply_to or "", step[n.reply_to], n)
                for n in notes if n.reply_to in ids
            ]
            out.append(Case(
                id=first, service=service, owner=owner, tasks=tasks, result=res, state=state,
                playbook=tasks[0].playbook or 0,
                used=version_at(timeline, msg_time(first_result) if (first_result := results.get(tasks[0].id)) else None),
                reworks=len(tasks) - 1, budget=sum(t.budget for t in tasks),
                runs=self._counter.runs_between(team, tasks[0].id[:21], end),
                lessons=[x for t in tasks if (r := results.get(t.id)) is not None and (x := lessons_of(r))],
                lesson_ids=[r.id for t in tasks if (r := results.get(t.id)) is not None and lessons_of(r)],
                verdicts=verdicts, started=msg_time(tasks[0]),
                finished=msg_time(res) if res is not None and final else None,
            ))
        return out

    def case_of(self, task: Message) -> Case | None:
        if not task.service or not self._agents.exists(task.to):
            return None
        return next((c for c in self.cases(task.to, task.service) if task.id in {t.id for t in c.tasks}), None)
