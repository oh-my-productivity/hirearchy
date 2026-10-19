"""Who you are and what is waiting for you: ``whoami`` and ``inbox``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..daemon import SchedulerStatus
from ..kernel import ROOT, Provider
from ..mail import BatchStore, MailboxReader
from ..prompts import Whoami
from ._ports import SetupMode, ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class IdentityTools(ToolGroup):
    def __init__(
        self, setup: SetupMode, whoami: Provider[Whoami], scheduler: Provider[SchedulerStatus], batches: Provider[BatchStore],
        mail: Provider[MailboxReader],
    ) -> None:
        self._setup = setup
        self._whoami = whoami
        self._scheduler = scheduler
        self._batches = batches
        self._mail = mail

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def whoami() -> str:
            """Your address, role, budget, direct reports, open tasks, outstanding delegations and charter."""
            if me == ROOT and self._setup.active():
                return self._setup.state()
            text = self._whoami().whoami(me)
            return f"{text}\n\n{self._scheduler().describe()}" if me == ROOT else text

        @mcp.tool()
        def inbox() -> str:
            """The messages for this run. For root (the human) this lists unread messages and marks them read."""
            if me == ROOT:
                batches = self._batches()
                batch = batches.begin(ROOT)
                batches.end(ROOT, ok=True)
            else:
                mail = self._mail()
                batch = mail.messages(me, "inflight") or mail.messages(me, "inbox")
            return "\n".join(m.render() for m in batch) or "(no new messages)"
