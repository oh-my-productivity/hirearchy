"""Providers of the ``review`` port (ARCHITECTURE.md 6.1).

The reviewer is composed here from the small role classes of the package: the run total, the ledger, the planner (which asks the health analyzer and the
reserve check), the cadence and the outbox. The run total and the ledger are shared by the reviewer and the cadence.
"""

from __future__ import annotations

from ..agents import AgentDirectory, RetiredArchive
from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..eligibility import PauseStore
from ..health import HealthAnalyzer
from ..kernel import Clock, EventSink, LedgerStore
from ..mail import TaskQuery
from ..review import HealthReviewer
from ..review._cadence import LedgerReviewCadence
from ..review._ledger import StoreReviewLedger
from ..review._outbox import DeliveryNoteOutbox
from ..review._planner import HealthReviewPlanner
from ..review._reserve import BudgetReserveCheck
from ..review._reviewer import LedgerHealthReviewer
from ..review._runs import ArchivedRunTotal
from ..runs import RunLogReader
from ..settings import OrgSettings
from ..templates import Notices
from ._builder import Builder
from ._lazy import PortResolver


def reviewer(b: PortResolver) -> LedgerHealthReviewer:
    """The reviewer over the ports ``b`` builds."""
    agents = b.get(AgentDirectory)
    total = ArchivedRunTotal(agents, b.get(RunLogReader), b.get(RetiredArchive))
    ledger = StoreReviewLedger(b.get(LedgerStore))
    planner = HealthReviewPlanner(
        agents, b.get(HealthAnalyzer), BudgetReserveCheck(b.get(PauseStore), b.get(BudgetQuery), b.get(TaskQuery)), b.get(Notices), total,
    )
    return LedgerHealthReviewer(
        planner, ledger, total, LedgerReviewCadence(ledger, total, b.get(OrgSettings)), DeliveryNoteOutbox(b.get(MessageDelivery)), b.get(EventSink),
        b.get(Clock),
    )


def register(b: Builder) -> None:
    b.provide(HealthReviewer, reviewer)
