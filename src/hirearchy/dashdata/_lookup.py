"""The wording of events, with the titles of the messages they are about."""

from __future__ import annotations

from ..kernel import JsonObject, Message
from ..mail import MailboxReader
from ._events import EventLine, event_lines
from ._ports import ReadableEvents

INDEXES_KEPT = 200  # mailboxes whose listing is kept as a dictionary by message id


class MailWordedEvents(ReadableEvents):
    """Events as lines a human reads. The messages of a run's batch are looked up in the mailboxes: one dictionary per mailbox listing,
    rebuilt only when the listing changed (the caching mailbox hands out the very same list while nothing changed)."""

    def __init__(self, mailbox: MailboxReader) -> None:
        self._mailbox = mailbox
        self._index: dict[str, tuple[list[Message], dict[str, Message]]] = {}

    def lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        return event_lines(events, me=me, actor=actor, raw=raw, lookup=self.message)

    def message(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        try:
            merged = self._mailbox.messages(agent, "inbox", "inflight", "read")
        except Exception:  # noqa: BLE001
            return None
        hit = self._index.get(agent)
        if hit is None or hit[0] is not merged:
            hit = (merged, {m.id: m for m in merged})
            self._index[agent] = hit
            if len(self._index) > INDEXES_KEPT:
                self._index.pop(next(iter(self._index)))
        m = hit[1].get(mid)
        return (m.type, m.title, m.sender) if m is not None else None
