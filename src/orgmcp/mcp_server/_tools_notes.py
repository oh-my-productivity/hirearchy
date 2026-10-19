"""Notes and budget between neighbours: ``send`` and ``reclaim``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..budget import BudgetQuery, BudgetReclaimer
from ..dispatch import MessageSender
from ..kernel import ROOT, Provider, parent
from ._ports import ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class NoteTools(ToolGroup):
    def __init__(self, sender: Provider[MessageSender], budgets: Provider[BudgetQuery], reclaimer: Provider[BudgetReclaimer]) -> None:
        self._sender = sender
        self._budgets = budgets
        self._reclaimer = reclaimer

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def send(to: str, body: str, title: str = "", reply_to: str | None = None, budget: int = 0) -> str:
            """Send a note: a question, information, or an escalation.

        Allowed recipients: your parent, your direct reports, your siblings, or the sender of the message
        you reply to (set reply_to to its id). budget: runs to move along with the note (optional): extra runs
        granted to a direct report, or unneeded runs given back to your PARENT (never to a sibling). Runs you
        have left return to your parent by themselves with your final `done`/`failed` report when nothing else
        is open for you; use this only to give some back earlier. To pull unspent runs BACK from an idle direct
        report instead (budget stranded in a team that cannot use it), use `reclaim`.
        """
            msg = self._sender().send(me, to, body, title=title, reply_to=reply_to, budget=budget)
            moved = f" with {msg.budget} run(s) of budget" if msg.budget else ""
            hint = self._budgets().grant_hint(msg.to) if msg.budget and parent(msg.to) == me else ""
            return f"sent {msg.id} to {msg.to}{moved}" + (f". {hint}" if hint else "")

        @mcp.tool()
        def reclaim(report: str, budget: int | None = None) -> str:
            """Pull unspent budget back from one of your DIRECT reports (a manager from its team; root from its top agents).

        report: its short name or address. budget: how many runs (default: all it has left). Only an idle report:
        no open task, nothing delegated and outstanding, not running, no unread mail that would wake it; otherwise the
        call is refused and says why. Not from deeper down (a manager reclaims from its own reports). The report is
        not woken and gets no message; you get the runs (they join your budget at once, and then a delegation or
        `send(..., budget=N)` can move them to whoever needs them). Use it before asking your parent for more runs
        while a sibling team sits on unspent ones.
        """
            msg = self._reclaimer().reclaim(me, report, budget)
            left = "" if me == ROOT else f" Your budget is now {self._budgets().budget(me)}."
            return f"reclaimed {msg.budget} run(s) from {msg.sender}.{left}"
