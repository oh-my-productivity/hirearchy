"""Could an agent of a team run (moved from ``progress._can_run`` and ``_alive``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..eligibility import RunnableQuery
from ..mail import MailboxReader
from ._ports import TeamLiveness


class RunnableTeams(TeamLiveness):
    def __init__(self, mail: MailboxReader, runnable: RunnableQuery) -> None:
        self._mail = mail
        self._runnable = runnable

    def can_run(self, addr: str) -> bool:
        return self._mail.has_inflight(addr) or self._runnable.startable(addr)

    def alive(self, team: Sequence[str]) -> bool:
        return any(self.can_run(a) for a in team)
