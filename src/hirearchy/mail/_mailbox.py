"""The mailboxes on disk: ``<addr>/{inbox,inflight,read,sent}/*.md`` (the boxes of root are in the organization directory itself)."""

from __future__ import annotations

import os
from pathlib import Path

from ..kernel import BOXES, RUNTIME, AtomicWriter, Message, OrgLayout, visible
from ._reads import DerivedMailboxReads
from ._rules import RECEIVED_BOXES, is_message_name, is_plain_id
from ._wakes import wakes
from .api import MailboxWriter, MailFingerprint, MessageParser


class FsMailbox(DerivedMailboxReads, MailboxWriter, MailFingerprint):
    """Reads message files through the parser (whose cache makes a second read cheap) and writes them through the atomic writer."""

    def __init__(self, layout: OrgLayout, parser: MessageParser, writer: AtomicWriter) -> None:
        self._layout = layout
        self._parser = parser
        self._writer = writer

    # ------------------------------------------------------------------ MailboxReader

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        """The messages of the boxes, sorted by id.

        A file listed in a received box that is gone when it is read has been moved by the batch store (``inbox`` -> ``inflight`` -> ``read``, or
        back): it is read at its new place when that is another received box this call asked for, and is otherwise left out of this call. A message
        read at a new place is returned once per call. A ``sent`` file that is gone, and every other error, raise.
        """
        out: list[Message] = []
        moved: set[str] = set()  # the names this call read at a new place: the walk may meet them again in the box they moved to
        for box in boxes:
            d = self._layout.box(addr, box)
            if not d.is_dir():
                continue
            for p in visible(d.glob("*.md")):
                if p.name in moved:
                    continue
                try:
                    out.append(self._parser.parse(p))
                except FileNotFoundError:
                    if box not in RECEIVED_BOXES:
                        raise
                    found = self._read_where_it_moved(addr, p.name, box, boxes)
                    if found is not None:
                        out.append(found)
                        moved.add(p.name)
        return sorted(out, key=lambda m: m.id)

    def _read_where_it_moved(self, addr: str, name: str, gone_from: str, boxes: tuple[str, ...]) -> Message | None:
        """The message file ``name`` in another received box the call asked for (in ``RECEIVED_BOXES`` order), or ``None`` when it is nowhere."""
        for box in RECEIVED_BOXES:
            if box == gone_from or box not in boxes:
                continue
            try:
                return self._parser.parse(self._layout.box(addr, box) / name)
            except FileNotFoundError:
                continue
        return None

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        if not is_plain_id(msg_id):
            return None
        for box in BOXES:
            p = self._layout.box(addr, box) / f"{msg_id}.md"
            if p.is_file():
                try:
                    return self._parser.parse(p)
                except Exception:  # noqa: BLE001 - a file that does not parse is no answer
                    return None
        return None

    def unread(self, addr: str) -> int:
        """Messages in the inbox that wake the agent: what makes it runnable and what health calls "unread mail".

        Non-waking messages (``wake: false``) sit in the inbox uncounted and join the batch of its next real run.
        """
        d = self._layout.box(addr, "inbox")
        return sum(1 for p in visible(d.glob("*.md")) if self._wakes(p)) if d.is_dir() else 0

    def _wakes(self, path: Path) -> bool:
        return wakes(self._parser, path)

    def has_inflight(self, addr: str) -> bool:
        d = self._layout.box(addr, "inflight")
        return d.is_dir() and bool(visible(d.glob("*.md")))

    # ------------------------------------------------------------------ MailboxWriter

    def store(self, msg: Message) -> None:
        text = msg.to_text()
        # Sender's copy first: it is what charges a budget grant. A failure between the two writes can then only
        # leave a message charged but undelivered (recover() re-delivers it), never delivered but uncharged.
        if msg.sender != RUNTIME:
            self._writer.write(self._layout.box(msg.sender, "sent") / f"{msg.id}.md", text)
        self._writer.write(self._layout.box(msg.to, "inbox") / f"{msg.id}.md", text)

    # ------------------------------------------------------------------ MailFingerprint

    def fingerprint(self, addr: str) -> tuple[frozenset[str], frozenset[str]]:
        def names(*boxes: str) -> frozenset[str]:
            out: set[str] = set()
            for box in boxes:
                try:
                    out.update(n for n in os.listdir(self._layout.box(addr, box)) if is_message_name(n))
                except OSError:
                    pass
            return frozenset(out)

        return names(*RECEIVED_BOXES), names("sent")
