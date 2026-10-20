"""``MailMessageViews``: the messages of an agent as rows, and one message as text."""

from __future__ import annotations

from ..kernel import BOXES, stamp_of
from ..mail import MailboxReader, MessageParser
from ._const import TEXT_CAP
from ._data import MsgRow
from ._ports import MessageViews
from ._text import clean_text


class MailMessageViews(MessageViews):
    def __init__(self, mailbox: MailboxReader, parser: MessageParser) -> None:
        self._mailbox = mailbox
        self._parser = parser

    def rows(self, addr: str, limit: int = 300) -> list[MsgRow]:
        rows: list[MsgRow] = []
        for box in BOXES:
            for m in self._mailbox.messages(addr, box):
                rows.append(MsgRow(m.id, box, m.type, m.sender, m.to, m.title, m.status, m.budget, stamp_of(m.id), m.path))
        rows.sort(key=lambda r: (r.id, r.box))
        return rows[-limit:][::-1]  # newest first

    def text(self, row: MsgRow) -> str:
        """The message as ``Message.render`` shows it, whole (capped), or why it cannot be read."""
        try:
            m = self._parser.parse(row.path) if row.path else None
        except Exception as exc:  # noqa: BLE001
            return f"cannot read {row.path}: {type(exc).__name__}: {exc}"
        if m is None:
            return "(message file is gone)"
        body = m.render(limit=0)
        return clean_text(body[:TEXT_CAP] + (f"\n[... {len(body) - TEXT_CAP} more characters in {row.path}]" if len(body) > TEXT_CAP else ""))
