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
from ..progress import ProgressReporter
from ..progress._activity import FsTeamActivity
from ..progress._counts import LogRunCounts
from ..progress._lines import CaseTaskLines
from ..progress._listing import MailRootTasks
from ..progress._liveness import RunnableTeams
from ..progress._render import RootTaskReport
from ..progress._reporter import DerivedProgressReporter
from ..progress._snapshot import TeamSnapshots
from ..progress._states import MailTaskStates
from ..progress._teams import AgentTaskTeams
from ..progress._wait import PollingProgress
from ..reflection import CaseHistory, ServiceReports
from ..runs import RunLogReader
from ._builder import Builder
from ._lazy import PortResolver


def reporter(b: PortResolver) -> DerivedProgressReporter:
    """The reporter over the mailboxes, agents, flags, run logs, files, cases, queue, scheduler status and decision of ``b``."""
    mail, clock, queue = b.get(MailboxReader), b.get(Clock), b.get(HumanQueue)
    roots, teams, states = MailRootTasks(mail), AgentTaskTeams(b.get(AgentDirectory)), MailTaskStates(mail, b.get(PauseStore), b.get(TaskQuery))
    lines = CaseTaskLines(
        teams, states, LogRunCounts(mail, b.get(RunLogReader)), FsTeamActivity(b.get(OrgLayout)), b.get(CaseHistory), b.get(ServiceReports), mail,
    )
    snapshots = TeamSnapshots(roots, teams, states, RunnableTeams(mail, b.get(RunnableQuery)), queue, clock)
    return DerivedProgressReporter(
        PollingProgress(RootTaskReport(roots, lines, queue, clock), snapshots, clock), snapshots, b.get(SchedulerStatus), b.get(WaitingOnUser),
        b.get(TaskQuery),
    )


def register(b: Builder) -> None:
    b.provide(ProgressReporter, reporter)
