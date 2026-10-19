"""``MailClientRework``: which of the reworks an agent received come from the client of a service case, not from its manager."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..agents import AgentDirectory
from ..kernel import ROOT, Message, latest_results
from ..mail import MailboxReader
from ._ports import ClientRework


class MailClientRework(ClientRework):
    def __init__(self, agents: AgentDirectory, mail: MailboxReader) -> None:
        self._agents = agents
        self._mail = mail

    def driven(self, tasks: Sequence[Message], results: Mapping[str, Message]) -> set[str]:
        """Ids of the received reworks (tasks with ``revises``) that stem from the client of a service case.

        * a rework *request* of a service (``service`` set) whose revised task had already been reported ``done``: the
          client looked at a delivery and sent it back;
        * a rework the sender sent its team (e.g. "check the memo again") while it held such a client rework as an open
          task: a consequence of the client's rejection, not of the receiver's own work.

        A rework sent in answer to a failed, blocked or still open task is the manager's own quality control and counts.
        """
        return self._driven(tasks, results, 0)

    def _driven(self, tasks: Sequence[Message], results: Mapping[str, Message], _depth: int) -> set[str]:
        out: set[str] = set()
        for t in tasks:
            if not t.revises:
                continue
            prior = results.get(t.revises)
            if t.service and prior is not None and prior.status == "done" and prior.id < t.id:
                out.add(t.id)
            elif _depth < 8 and t.sender != ROOT and self._agents.exists(t.sender) and self._holds_client_rework(t, _depth):
                out.add(t.id)
        return out

    def _holds_client_rework(self, task: Message, depth: int) -> bool:
        """Did ``task``'s sender hold a client-driven rework as an open task when it sent ``task``?"""
        sender = task.sender
        mine = [m for m in self._mail.received(sender) if m.type == "task"]
        answers = latest_results(self._mail.sent(sender))
        driven = self._driven(mine, answers, depth + 1)
        return any(
            m.id in driven and m.id < task.id and (m.id not in answers or answers[m.id].id > task.id) for m in mine
        )
