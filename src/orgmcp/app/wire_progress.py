"""Providers of the ``progress`` ports (ARCHITECTURE.md 6.1), and the parts the legacy functions of the package ask for.

The reporter is built from the ports of the organization it reports on; the small parts a report is made of (who the team of a task is, its state, the
runs it made, when it last did anything, whether anyone could still run, the lines, the snapshots of a wait) are private to the package and made here,
inside the provider of the port that uses them.

``RuntimeParts`` serves ``progress.progress`` / ``describe_progress`` / ``work_in_flight`` (the permanent ``progress(org, task_id)`` of the README among
them) and the private names the dashboard, the scheduler and ``observe`` still import: they are handed an ``Org`` whose ``runtime`` tests replace (the
runnable query, the process table) and the dashboard's lenient ``Org`` replaces the mailboxes, the agents, the budgets and the pause flags of, so each call
asks for the queue of what needs the user, the history of the cases, the scheduler status and the decision of the user over the ports the runtime has
*now*, as the functions they replace read them through the ``Org``. They go when the legacy functions do (E3).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from ..agents import AgentDirectory
from ..attention import HumanQueue, WaitingOnUser
from ..daemon import SchedulerStatus
from ..eligibility import PauseStore, RunnableQuery
from ..kernel import Clock, OrgLayout
from ..mail import MailboxReader, TaskQuery
from ..progress import LegacyParts, ProgressReporter
from ..progress._activity import FsTeamActivity
from ..progress._lines import CaseTaskLines
from ..progress._listing import MailRootTasks
from ..progress._liveness import RunnableTeams
from ..progress._render import RootTaskReport
from ..progress._reporter import DerivedProgressReporter
from ..progress._counts import LogRunCounts
from ..progress._snapshot import TeamSnapshots
from ..progress._states import MailTaskStates
from ..progress._teams import AgentTaskTeams
from ..progress._wait import PollingProgress
from ..reflection import CaseHistory, ServiceReports
from ..reflection._assembly import history_of, reports_of
from ..runs import RunLogReader
from ._builder import Builder
from ._lazy import PortResolver
from .runtime import OrgRuntime
from .wire_attention import human_queue_of, waiting_on_user_of
from .wire_daemon import status_of


def reporter(b: PortResolver) -> DerivedProgressReporter:
    """The reporter over the mailboxes, agents, flags, run logs, files, cases, queue, scheduler status and decision of ``b``."""
    mail, clock, queue = b.get(MailboxReader), b.get(Clock), b.get(HumanQueue)
    roots, teams, states = MailRootTasks(mail), AgentTaskTeams(b.get(AgentDirectory)), MailTaskStates(mail, b.get(PauseStore), b.get(TaskQuery))
    lines = CaseTaskLines(
        teams, states, LogRunCounts(mail, b.get(RunLogReader)), FsTeamActivity(b.get(OrgLayout)), b.get(CaseHistory), b.get(ServiceReports),
    )
    snapshots = TeamSnapshots(roots, teams, states, RunnableTeams(mail, b.get(RunnableQuery)), queue, clock)
    return DerivedProgressReporter(
        PollingProgress(RootTaskReport(roots, lines, queue, clock), snapshots, clock), snapshots, b.get(SchedulerStatus), b.get(WaitingOnUser),
        b.get(TaskQuery),
    )


class RuntimeParts(LegacyParts):
    """The objects the legacy functions cannot build, over the ports ``runtime`` has now."""

    def human_queue(self, runtime: object) -> HumanQueue:
        return human_queue_of(cast(OrgRuntime, runtime))

    def case_history(self, runtime: object) -> CaseHistory:
        return history_of(SimpleNamespace(runtime=runtime))

    def service_reports(self, runtime: object) -> ServiceReports:
        return reports_of(SimpleNamespace(runtime=runtime))

    def scheduler_status(self, runtime: object) -> SchedulerStatus:
        return status_of(cast(OrgRuntime, runtime))

    def waiting_on_user(self, runtime: object) -> WaitingOnUser:
        return waiting_on_user_of(cast(OrgRuntime, runtime))


def register(b: Builder) -> None:
    b.provide(ProgressReporter, reporter)
    b.provide(LegacyParts, lambda b: RuntimeParts())
