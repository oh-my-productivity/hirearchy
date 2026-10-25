"""Providers of the ``progress`` ports (ARCHITECTURE.md 6.1).

The reporter is built from the ports of the organization it reports on; the small parts a report is made of (who the team of a task is, its state, the
runs it made, when it last did anything, whether anyone could still run, the lines, the snapshots of a wait) are private to the package and made here,
inside the provider of the port that uses them.
"""

from __future__ import annotations

from ..agents import AgentDirectory
from ..attention import HumanQueue, WaitingOnUser
from ..daemon import SchedulerStatus
from ..eligibility import PauseStore, RunnableQuery
from ..kernel import Clock, OrgLayout
from ..mail import MailboxReader, TaskQuery
from ..budget import BudgetQuery
from ..progress import ProgressReporter, QualityReport
from ..progress._activity import FsTeamActivity
from ..progress._counts import LogRunCounts
from ..progress._lines import CaseTaskLines
from ..progress._listing import MailRootTasks
from ..progress._liveness import RunnableTeams
from ..progress._render import RootTaskReport
from ..progress._quality import DerivedQualityReport
from ..progress._reporter import DerivedProgressReporter
from ..progress._snapshot import TeamSnapshots
from ..progress._states import MailTaskStates
from ..progress._teams import AgentTaskTeams
from ..progress._wait import PollingProgress
from ..reflection import CaseHistory, CaseRecords, DeliverableChecks, ServiceReports
from ..runs import RunLogReader
from ..settings import OrgSettings
from ._builder import Builder
from ._fail_counts import HealthFailCounts
from ._lazy import PortResolver
from ._readable_config import ReadableOrgConfig
from .wire_health import escape_counter


def reporter(b: PortResolver) -> DerivedProgressReporter:
    """The reporter over the mailboxes, agents, flags, run logs, files, cases, queue, scheduler status and decision of ``b``."""
    mail, clock, queue = b.get(MailboxReader), b.get(Clock), b.get(HumanQueue)
    roots, teams, states = MailRootTasks(mail), AgentTaskTeams(b.get(AgentDirectory)), MailTaskStates(mail, b.get(PauseStore), b.get(TaskQuery))
    lines = CaseTaskLines(
        teams, states, LogRunCounts(mail, b.get(RunLogReader)), FsTeamActivity(b.get(OrgLayout)), b.get(CaseHistory), b.get(ServiceReports), mail,
    )
    snapshots = TeamSnapshots(roots, teams, states, RunnableTeams(mail, b.get(RunnableQuery)), queue, clock)
    return DerivedProgressReporter(
        PollingProgress(RootTaskReport(roots, lines, queue, clock, b.get(DeliverableChecks)), snapshots, clock), snapshots, b.get(SchedulerStatus), b.get(WaitingOnUser),
        b.get(TaskQuery),
    )


def quality_report(b: PortResolver) -> DerivedQualityReport:
    """The quality view over the records of the cases, the states and teams of the tasks, the budgets, health's FAIL counts and ORG.md of ``b``."""
    mail = b.get(MailboxReader)
    return DerivedQualityReport(
        b.get(CaseRecords), MailTaskStates(mail, b.get(PauseStore), b.get(TaskQuery)), AgentTaskTeams(b.get(AgentDirectory)), b.get(TaskQuery), mail,
        b.get(BudgetQuery), b.get(AgentDirectory), HealthFailCounts(escape_counter(b)), ReadableOrgConfig(b.get(OrgSettings)),
    )


def register(b: Builder) -> None:
    b.provide(ProgressReporter, reporter)
    b.provide(QualityReport, quality_report)
