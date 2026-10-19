"""``SoleUpstreamTask``: the one task a delegation probably serves (moved from ``Org._upstream``)."""

from __future__ import annotations

from ..kernel import Message, latest_results
from ..mail import MailboxReader
from ._ports import UpstreamTasks


class SoleUpstreamTask(UpstreamTasks):
    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        """The one task of ``addr`` that a delegation probably serves, with its latest result (None = still open).

        A candidate was assigned before the delegation and is open, reported ``blocked`` or was reported only after
        the delegation. None when there is not exactly one candidate.
        """
        latest = latest_results(self._mail.sent(addr))
        found = [
            (t, latest.get(t.id)) for t in self._mail.received(addr)
            if t.type == "task" and t.id < delegated.id
            and ((r := latest.get(t.id)) is None or r.status == "blocked" or r.id > delegated.id)
        ]
        return found[0] if len(found) == 1 else None
