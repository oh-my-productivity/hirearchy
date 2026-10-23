"""(b) Budget conservation."""

from __future__ import annotations

from collections.abc import Sequence

from ...agents import AgentDirectory, RetiredArchive
from ...budget import BudgetQuery
from ...kernel import ROOT, JsonObject, Message, is_run_credit, norm
from ...mail import MessageFile
from ...runs import RunLogReader
from .._ports import IntegrityCheck
from ._base import COPY_GRACE, RECV_BOXES, runs_of, verdict


class BudgetConserved(IntegrityCheck):
    """Budget conservation.

    Budget is derived from messages and run logs (``BudgetQuery.budget`` = received - handed down - run logs). Runs of budget enter only from root (a
    task's or a note's ``budget`` in root's ``sent/``); they leave in four ways, and nothing else: held by an agent now (the sum of ``budget``), consumed
    (run logs of live agents, and of retired agents, see ``RetiredArchive.run_count``), returned to root (the ``budget`` of messages root received:
    results and notes), or dropped when a top-level agent was retired (root has no limit, so its team's unspent runs are not refunded; retired deeper in
    the tree they are refunded to the parent by a runtime note, which cancels out). Hence::

        handed down by root == held + used (live + retired) + returned to root + dropped at retirement

    A message being delivered right now (sender copy written, recipient copy not yet, younger than ``COPY_GRACE``) is charged but not yet credited; it is
    counted as "in delivery" so a live check does not fail on it.

    A run credit (the runtime's note that returns a run it did not charge: ``kernel.is_run_credit``) is budget that enters from the runtime, not from root:
    ``handed down + credited`` is what the right side holds, with the credits of live agents counted from their received boxes and the credits of
    retired agents from ``RetiredArchive.credited``. The equation text names the credits only when there are some.
    """

    def __init__(self, agents: AgentDirectory, budgets: BudgetQuery, run_logs: RunLogReader, archive: RetiredArchive) -> None:
        self._agents, self._budgets, self._run_logs, self._archive = agents, budgets, run_logs, archive

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        handed = sum(runs_of(f) for f in files if not f.error and f.owner == ROOT and f.box == "sent")
        returned = sum(runs_of(f) for f in files if not f.error and f.owner == ROOT and f.box in RECV_BOXES)
        try:
            held = sum(self._budgets.budget(a) or 0 for a in self._agents.agents())
        except Exception as exc:  # noqa: BLE001 - a corrupt message makes the arithmetic impossible; (a) names the file
            return verdict("b", "budget conserved", [f"cannot compute the agents' budgets: {type(exc).__name__}: {exc}"])
        used_live = sum(self._run_logs.count(a) for a in self._agents.agents())
        used_retired = self._archive.run_count()
        dropped = sum(self._archive.unspent_budget(tree) for tree in self._archive.trees() if tree.top_level)
        credited = sum(runs_of(f) for f in files if not f.error and f.box in RECV_BOXES and self._credit(f)) + self._archive.credited()
        delivered = {f.id for f in files if not f.error and f.box in RECV_BOXES}
        pending = sum(
            runs_of(f)
            for f in files
            if not f.error and f.box == "sent" and f.id not in delivered and now - f.mtime <= COPY_GRACE
            and self._agents.exists(norm(str((f.meta or {}).get("to"))))
        )
        rhs = held + used_live + used_retired + returned + dropped + pending
        eq = (f"handed down {handed}" + (f" + {credited} credited" if credited else "") + f" = held {held} + used {used_live} live + {used_retired} retired "
              f"+ returned {returned} + dropped {dropped}" + (f" + {pending} in delivery" if pending else ""))
        handed += credited
        if handed == rhs:
            return verdict("b", "budget conserved: handed down = held + used + returned (+ dropped at retirement)", [], eq)
        diff = handed - rhs
        return verdict("b", "budget conserved: handed down = held + used + returned (+ dropped at retirement)",
                       [f"{eq}: {abs(diff)} run(s) {'vanished' if diff > 0 else 'appeared from nowhere'} (difference {diff:+d})"])

    @staticmethod
    def _credit(f: MessageFile) -> bool:
        """The message file is a run credit (its front matter says so)."""
        try:
            return is_run_credit(Message.from_parts(f.meta or {}, ""))
        except Exception:  # noqa: BLE001 - a front matter that is not a message (a budget that is no number): not a credit
            return False
