"""Mailboxes, task queries and the run lifecycle of the inbox (mail).

The bodies call the ports of ``self.runtime`` (step A-mail; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Message
from .runtime import OrgRuntime
from .wiring import process_resources


class MailMixin:
    """Mailboxes, task queries and the run lifecycle of the inbox (mail)."""

    runtime: OrgRuntime

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        return self.runtime.mailbox.messages(addr, *boxes)

    def received(self, addr: str) -> list[Message]:
        return self.runtime.mailbox.received(addr)

    def sent(self, addr: str) -> list[Message]:
        return self.runtime.mailbox.sent(addr)

    def unread(self, addr: str) -> int:
        """Messages in the inbox that wake the agent: what makes it runnable and what health calls "unread mail".

        Non-waking messages (``wake: false``) sit in the inbox uncounted and join the batch of its next real run.
        """
        return self.runtime.mailbox.unread(addr)

    @staticmethod
    def _wakes(path: Path) -> bool:
        """Does this inbox file wake its agent? (The mailbox does this itself; the static spelling is the legacy one.)"""
        try:
            return process_resources().message_parser.parse(path).wake
        except Exception:  # noqa: BLE001 - an unreadable file still counts as mail: a run should look at it
            return True

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        return self.runtime.mailbox.find_received(addr, msg_id)

    def open_tasks(self, addr: str) -> list[Message]:
        return self.runtime.task_query.open_tasks(addr)

    def outstanding(self, addr: str) -> list[Message]:
        return self.runtime.task_query.outstanding(addr)

    def begin_run(self, addr: str) -> list[Message]:
        """Move the inbox into inflight/: that batch is what this run handles (held non-waking messages included)."""
        return self.runtime.batches.begin(addr)

    def end_run(self, addr: str, ok: bool) -> None:
        """Success: the batch is processed. Failure: put it back for a retry (at-least-once).

        A no-op for an agent that no longer exists (retired while its run was in flight): its directory is gone,
        and creating the mailbox again would leave a ghost directory behind.
        """
        self.runtime.batches.end(addr, ok)

    def recover(self) -> list[str]:
        """After a crash: return every inflight batch to its inbox, and finish interrupted deliveries.

        Returns the agents whose interrupted run was recovered (see :meth:`redeliver_orphans` for the other part).
        """
        return self.runtime.batches.recover()

    def redeliver_orphans(self) -> list[str]:
        """Deliver every sent message whose recipient has no copy (``deliver`` writes ``sent/`` first).

        A message is delivered when its id is in the recipient's inbox, inflight or read; ids are unique across the
        organization, so one scan of the file names finds the orphans without parsing the whole history. Messages
        to agents that no longer exist are left alone. Returns the ids that were re-delivered.
        """
        return self.runtime.batches.redeliver_orphans()

    def running(self, addr: str) -> bool:
        return self.runtime.mailbox.has_inflight(addr)

    def _blocked_tasks(self, addr: str) -> list[Message]:
        """Tasks assigned to ``addr`` whose latest result is ``blocked``: answered, but they may be reported again."""
        return self.runtime.task_query.blocked_tasks(addr)
