"""``InboxHumanQueue``: the unread messages of root that wait for a decision (moved from ``progress._human_items`` and ``_needs_human``)."""

from __future__ import annotations

from ..kernel import ROOT
from ..mail import MailboxReader
from ._text import short, summary
from .api import HumanQueue


class InboxHumanQueue(HumanQueue):
    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def items(self) -> list[tuple[str, str]]:
        out = []
        for m in self._mail.messages(ROOT, "inbox"):
            if not m.wake or (m.type == "result" and m.status == "done"):
                continue
            if m.type == "result":
                what, text = f"{m.status} result from {m.sender}", summary(m.body)
            else:
                what = "runtime notice" if m.sender == "runtime" else f"note from {m.sender}"
                text = next((line.strip() for line in m.body.splitlines() if line.strip()), "")
            title = f' "{m.title}"' if m.title else ""
            out.append((m.id, f"Needs you: {what}{title}" + (f": {short(text)}" if text else "") + f" (message {m.id})"))
        return out

    def lines(self) -> list[str]:
        """One line per item that waits for the human."""
        return [line for _, line in self.items()]
