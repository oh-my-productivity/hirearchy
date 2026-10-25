"""``SoleUpstreamTask``: the one task a delegation probably serves (moved from ``Org._upstream``)."""

from __future__ import annotations

from ..kernel import Message, latest_results
from ..mail import MailboxReader, still_open
from ._ports import UpstreamTasks


class SoleUpstreamTask(UpstreamTasks):
    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        """The one task of ``addr`` that a delegation probably serves, with its latest result (None = still open).

        A candidate was assigned before the delegation and was still open when it was sent: no result, a result only after the delegation, or a
        ``blocked`` one its assigner had not moved past by then (``mail.still_open`` over what ``addr`` had received before the delegation; D-E7-2
        F-E7-7). None when there is not exactly one candidate.
        """
        latest = latest_results(self._mail.sent(addr))
        received = self._mail.received(addr)
        before = [m for m in received if m.id < delegated.id]  # what addr had received when it delegated
        found = [
            (t, latest.get(t.id)) for t in received if t.type == "task" and t.id < delegated.id
            and ((r := latest.get(t.id)) is None or r.id > delegated.id or still_open(t, r, before))
        ]
        return found[0] if len(found) == 1 else None
