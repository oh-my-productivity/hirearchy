"""The batch of a run between the boxes: ``inbox`` -> ``inflight`` -> ``read`` (or back to ``inbox``), and the recovery after a crash."""

from __future__ import annotations

import os

from ..agents import AgentDirectory
from ..kernel import ROOT, AtomicWriter, Message, OrgLayout, norm, visible
from ._rules import RECEIVED_BOXES
from .api import BatchStore, MailboxReader, MessageParser


class FsBatchStore(BatchStore):
    """Moves message files between the boxes of an agent; the only writer of ``inflight`` and ``read``."""

    def __init__(
        self, layout: OrgLayout, agents: AgentDirectory, reader: MailboxReader, parser: MessageParser, writer: AtomicWriter
    ) -> None:
        self._layout = layout
        self._agents = agents
        self._reader = reader
        self._parser = parser
        self._writer = writer

    def begin(self, addr: str) -> list[Message]:
        """Move the inbox into inflight/: that batch is what this run handles (held non-waking messages included)."""
        d = self._layout.agent_dir(addr)
        (d / "inflight").mkdir(exist_ok=True)
        for p in visible((d / "inbox").glob("*.md")):
            os.replace(p, d / "inflight" / p.name)
        return self._reader.messages(addr, "inflight")

    def end(self, addr: str, ok: bool) -> None:
        """Success: the batch is processed. Failure: put it back for a retry (at-least-once).

        A no-op for an agent that no longer exists (retired while its run was in flight): its directory is gone,
        and creating the mailbox again would leave a ghost directory behind.
        """
        if not self._agents.exists(addr):
            return
        d = self._layout.agent_dir(addr)
        target = d / ("read" if ok else "inbox")
        target.mkdir(exist_ok=True)
        for p in visible((d / "inflight").glob("*.md")):
            os.replace(p, target / p.name)

    def recover(self) -> list[str]:
        """After a crash: return every inflight batch to its inbox, and finish interrupted deliveries.

        Returns the agents whose interrupted run was recovered (see :meth:`redeliver_orphans` for the other part).
        """
        out = []
        for a in self._agents.agents():
            if self._reader.messages(a, "inflight"):
                self.end(a, ok=False)
                out.append(a)
        self.redeliver_orphans()
        return out

    def redeliver_orphans(self) -> list[str]:
        """Deliver every sent message whose recipient has no copy (``deliver`` writes ``sent/`` first).

        A message is delivered when its id is in the recipient's inbox, inflight or read; ids are unique across the
        organization, so one scan of the file names finds the orphans without parsing the whole history. Messages
        to agents that no longer exist are left alone. Returns the ids that were re-delivered.
        """
        owners = [ROOT, *self._agents.agents()]
        have = {
            p.stem
            for a in owners
            for box in RECEIVED_BOXES
            if self._layout.box(a, box).is_dir()
            for p in visible(self._layout.box(a, box).glob("*.md"))
        }
        out = []
        for a in owners:
            d = self._layout.box(a, "sent")
            for p in visible(d.glob("*.md")) if d.is_dir() else []:
                if p.stem in have:
                    continue
                try:
                    msg = self._parser.parse(p)
                except Exception:  # noqa: BLE001 - an unreadable file is not ours to fix here
                    continue
                to = norm(msg.to)
                if self._agents.exists(to):
                    self._writer.write(self._layout.box(to, "inbox") / p.name, p.read_text(encoding="utf-8"))
                    out.append(msg.id)
        return out
