"""Mailboxes, task queries and the run lifecycle of the inbox (mail).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

import os
from pathlib import Path

from ..kernel import latest_results, Message, ROOT, visible as _visible
from ._compat import atomic_write


class MailMixin:
    """Mailboxes, task queries and the run lifecycle of the inbox (mail)."""

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        out = []
        for box in boxes:
            d = self.dir(addr) / box
            if d.is_dir():
                out += [Message.load(p) for p in _visible(d.glob("*.md"))]
        return sorted(out, key=lambda m: m.id)

    def received(self, addr: str) -> list[Message]:
        return self.messages(addr, "inbox", "inflight", "read")

    def sent(self, addr: str) -> list[Message]:
        return self.messages(addr, "sent")

    def unread(self, addr: str) -> int:
        """Messages in the inbox that wake the agent: what makes it runnable and what health calls "unread mail".

        Non-waking messages (``wake: false``) sit in the inbox uncounted and join the batch of its next real run.
        """
        d = self.dir(addr) / "inbox"
        return sum(1 for p in _visible(d.glob("*.md")) if self._wakes(p)) if d.is_dir() else 0

    @staticmethod
    def _wakes(path: Path) -> bool:
        try:
            return Message.load(path).wake
        except Exception:  # noqa: BLE001 - an unreadable file still counts as mail: a run should look at it
            return True

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        return next((m for m in self.received(addr) if m.id == msg_id), None)

    def open_tasks(self, addr: str) -> list[Message]:
        a = self.norm(addr)
        answered = {m.reply_to for m in self.sent(a) if m.type == "result"}
        return [m for m in self.received(a) if m.type == "task" and m.id not in answered]

    def outstanding(self, addr: str) -> list[Message]:
        a = self.norm(addr)
        answered = {m.reply_to for m in self.received(a) if m.type == "result"}
        return [m for m in self.sent(a) if m.type == "task" and m.id not in answered]

    def begin_run(self, addr: str) -> list[Message]:
        """Move the inbox into inflight/: that batch is what this run handles (held non-waking messages included)."""
        d = self.dir(addr)
        (d / "inflight").mkdir(exist_ok=True)
        for p in _visible((d / "inbox").glob("*.md")):
            os.replace(p, d / "inflight" / p.name)
        return self.messages(addr, "inflight")

    def end_run(self, addr: str, ok: bool) -> None:
        """Success: the batch is processed. Failure: put it back for a retry (at-least-once).

        A no-op for an agent that no longer exists (retired while its run was in flight): its directory is gone,
        and creating the mailbox again would leave a ghost directory behind.
        """
        if not self.exists(addr):
            return
        d = self.dir(addr)
        target = d / ("read" if ok else "inbox")
        target.mkdir(exist_ok=True)
        for p in _visible((d / "inflight").glob("*.md")):
            os.replace(p, target / p.name)

    def recover(self) -> list[str]:
        """After a crash: return every inflight batch to its inbox, and finish interrupted deliveries.

        Returns the agents whose interrupted run was recovered (see :meth:`redeliver_orphans` for the other part).
        """
        out = []
        for a in self.agents():
            if self.messages(a, "inflight"):
                self.end_run(a, ok=False)
                out.append(a)
        self.redeliver_orphans()
        return out

    def redeliver_orphans(self) -> list[str]:
        """Deliver every sent message whose recipient has no copy (``deliver`` writes ``sent/`` first).

        A message is delivered when its id is in the recipient's inbox, inflight or read; ids are unique across the
        organization, so one scan of the file names finds the orphans without parsing the whole history. Messages
        to agents that no longer exist are left alone. Returns the ids that were re-delivered.
        """
        owners = [ROOT, *self.agents()]
        have = {
            p.stem
            for a in owners
            for box in ("inbox", "inflight", "read")
            if (self.dir(a) / box).is_dir()
            for p in _visible((self.dir(a) / box).glob("*.md"))
        }
        out = []
        for a in owners:
            d = self.dir(a) / "sent"
            for p in _visible(d.glob("*.md")) if d.is_dir() else []:
                if p.stem in have:
                    continue
                try:
                    msg = Message.load(p)
                except Exception:  # noqa: BLE001 - an unreadable file is not ours to fix here
                    continue
                to = self.norm(msg.to)
                if self.exists(to):
                    atomic_write(self.dir(to) / "inbox" / p.name, p.read_text(encoding="utf-8"))
                    out.append(msg.id)
        return out

    def running(self, addr: str) -> bool:
        d = self.dir(addr) / "inflight"
        return d.is_dir() and bool(_visible(d.glob("*.md")))

    def _blocked_tasks(self, addr: str) -> list[Message]:
        """Tasks assigned to ``addr`` whose latest result is ``blocked``: answered, but they may be reported again."""
        latest = latest_results(self.sent(addr))
        return [t for t in self.received(addr) if t.type == "task" and (r := latest.get(t.id)) and r.status == "blocked"]
