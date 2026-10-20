"""The reporter over an organization on disk and over memory, the fakes a consumer's test uses, and the registry the contract suites iterate over.

``ProgressWorld`` is an organization (agents, tasks, results, notes, run logs, pause flags, budgets) with the reporter over it: built over the files of a
temporary directory (``fs_world``) and over memory (``memory_world``), so that the reporter is tested against both. What the other packages say - the
history of the service cases, the queue of what needs the user, the status of the scheduler, the decision of the user - are their fakes, set by the
test (``history``, ``queue``, ``scheduler``, ``waiting``, ``totals``); the mailboxes, the agents, the flags, the run logs and what may start are real.

``FixedProgressReporter`` is what the tests of ``dashdata``, ``mcp_server`` and ``cli`` use instead of an organization: it answers what it is told to and
keeps a record of what it was asked.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..agents import AgentDirectory, AgentRegistry
from ..agents.testing import fs_agents
from ..attention.testing import FixedWaiting, ListHumanQueue
from ..budget.testing import BudgetWorld, FixedBudget
from ..budget.testing import fixed_world as memory_budget_world
from ..budget.testing import fs_world as fs_budget_world
from ..daemon.testing import FakeSchedulerStatus
from ..eligibility import PauseStore, RunnableQuery
from ..eligibility.testing import PauseHarness, fs_pauses, memory_pauses, runnable_over
from ..kernel import Clock, Message, OrgLayout, OrgPaths
from ..kernel.testing import FakeClock
from ..mail import MailboxReader, TaskQuery
from ..mail.testing import MemoryMailbox
from ..reflection import ServiceReports
from ..reflection.testing import FixedCaseHistory
from ..runs import RunLogReader
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ._activity import FsTeamActivity
from ._lines import CaseTaskLines
from ._liveness import RunnableTeams
from ._listing import MailRootTasks
from ._ports import ProgressText, ProgressView, Snapshot, Snapshots, TeamActivity
from ._render import RootTaskReport
from ._reporter import DerivedProgressReporter
from ._counts import LogRunCounts
from ._snapshot import TeamSnapshots
from ._states import MailTaskStates
from ._teams import AgentTaskTeams
from ._wait import PollingProgress
from .api import ProgressReporter

STAMP = "%Y%m%dT%H%M%S%f"

# ------------------------------------------------------------------------------ the fakes


class FixedProgressReporter(ProgressReporter):
    """``progress`` answers ``text``, ``describe_progress`` answers ``described`` (``text`` when not given), ``work_in_flight`` answers ``moving``; each
    call is kept in ``calls`` as ``(method, task_id, now, wait_seconds)``."""

    def __init__(self, text: str = "", described: str | None = None, moving: bool = False) -> None:
        self.text = text
        self.described = text if described is None else described
        self.moving = moving
        self.calls: list[tuple[str, str | None, datetime | None, int]] = []

    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        self.calls.append(("progress", task_id, now, wait_seconds))
        return self.text

    def describe_progress(self, task_id: str | None = None, wait_seconds: int = 0) -> str:
        self.calls.append(("describe_progress", task_id, None, wait_seconds))
        return self.described

    def work_in_flight(self, task_id: str | None = None) -> bool:
        self.calls.append(("work_in_flight", task_id, None, 0))
        return self.moving


class SpyProgressView(ProgressView):
    """The view answers ``text``; it keeps what it was asked in ``asked`` as ``(task_id, now, wait_seconds)``, and the keyword arguments it was given in ``kwargs``."""

    def __init__(self, text: str = "lines") -> None:
        self.text = text
        self.asked: list[tuple[str | None, datetime | None, int]] = []
        self.kwargs: dict[str, object] = {}

    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        self.asked.append((task_id, now, wait_seconds))
        self.kwargs.update(wait_seconds=wait_seconds)
        return self.text


class FixedSnapshots(Snapshots):
    """Every look is ``found`` (by default nothing is listed), and each is kept in ``asked``."""

    def __init__(self, found: Snapshot | None = None) -> None:
        self.found = found or Snapshot({}, {}, frozenset())
        self.asked: list[str | None] = []

    def snapshot(self, task_id: str | None) -> Snapshot:
        self.asked.append(task_id)
        return self.found


class FixedTeamActivity(TeamActivity):
    """The newest activity of an agent is the time in ``times`` (none: it did nothing); of a team the newest of its agents."""

    def __init__(self, times: Mapping[str, datetime] | None = None) -> None:
        self.times = dict(times or {})

    def newest(self, team: Sequence[str]) -> datetime | None:
        return max((self.times[a] for a in team if a in self.times), default=None)


class FixedCaseTotals(ServiceReports):
    """``case_total`` of a task is the text in ``totals`` (``""``: a task that is not a service request, or has no rework chain)."""

    def __init__(self, totals: Mapping[str, str] | None = None) -> None:
        self.totals = dict(totals or {})

    def services_text(self, actor: str) -> str:
        return ""

    def case_total(self, task: Message) -> str:
        return self.totals.get(task.id, "")


class ScriptedClock(Clock):
    """The time of ``inner``; ``sleep`` moves it and runs the action set for that sleep (``on_sleep(n, action)``); ``sleeps`` counts them."""

    def __init__(self, inner: FakeClock) -> None:
        self._inner = inner
        self.sleeps = 0
        self.slept: list[float] = []
        self._actions: dict[int, Callable[[], object]] = {}

    def on_sleep(self, n: int, action: Callable[[], object]) -> None:
        """Run ``action`` as the n-th sleep ends (the first is 1)."""
        self._actions[n] = action

    def now(self) -> datetime:
        return self._inner.now()

    def time(self) -> float:
        return self._inner.time()

    def monotonic(self) -> float:
        return self._inner.monotonic()

    def sleep(self, seconds: float) -> None:
        self.sleeps += 1
        self.slept.append(seconds)
        self._inner.sleep(seconds)
        action = self._actions.get(self.sleeps)
        if action is not None:
            action()


# ------------------------------------------------------------------------------ the world


@dataclass(frozen=True)
class ProgressWorld:
    """The reporter and the ports under it, and the means to prepare the organization. Addresses of agents: ``ceo``, ``ceo/eng``, ...; root exists."""

    reporter: ProgressReporter
    text: ProgressText
    snapshots: Snapshots
    mail: MailboxReader
    tasks: TaskQuery
    agents: AgentDirectory
    pauses: PauseStore
    runnable: RunnableQuery
    runs: RunLogReader
    layout: OrgLayout
    clock: ScriptedClock
    history: FixedCaseHistory
    totals: FixedCaseTotals
    queue: ListHumanQueue
    scheduler: FakeSchedulerStatus
    waiting: FixedWaiting
    activity: TeamActivity
    hire: Callable[[str], None]  # ``addr`` becomes an agent: no mail, no budget, no flag
    retire: Callable[[str], None]  # ``addr`` is retired (its directory is archived)
    delegate: Callable[[str, str, str, int], Message]  # (sender, to, title, runs): a task, delivered with the runs it carries
    answer: Callable[[Message, str, str, int], Message]  # (task, status, body, runs returned): the assignee reports; the result, delivered
    write: Callable[[str, str, str, str, int], Message]  # (sender, to, title, body, runs): a note that wakes, delivered
    use_run: Callable[[str], None]  # the agent makes one run: a log stamped now, and one run of its budget
    begin_run: Callable[[str], None]  # its inbox becomes the batch of a run in flight
    end_run: Callable[[str], None]  # the run ends well: the batch is read
    pause: Callable[[str, str], None]  # (addr, reason): the agent is paused
    advance: Callable[[float], None]  # time passes


def _world(
    tmp_path: Path, budgets: BudgetWorld, runs: RunsHarness, pauses: PauseHarness, registry: AgentRegistry, activity: Callable[[OrgLayout], TeamActivity],
    wait_clock: ScriptedClock,
) -> ProgressWorld:
    fixed: FixedBudget | None = budgets.fixed
    layout = OrgPaths(tmp_path)
    runnable = runnable_over(budgets.agents, budgets.mail, pauses.store, budgets.query)
    waiting = FixedWaiting()
    history, totals, queue, scheduler = FixedCaseHistory(), FixedCaseTotals(), ListHumanQueue(), FakeSchedulerStatus(waiting=waiting)
    team_activity = activity(layout)
    roots, teams, states = MailRootTasks(budgets.mail), AgentTaskTeams(budgets.agents), MailTaskStates(budgets.mail, pauses.store, budgets.tasks)
    lines = CaseTaskLines(teams, states, LogRunCounts(budgets.mail, runs.reader), team_activity, history, totals)
    snapshots = TeamSnapshots(roots, teams, states, RunnableTeams(budgets.mail, runnable), queue, wait_clock)
    text = RootTaskReport(roots, lines, queue, wait_clock)
    reporter = DerivedProgressReporter(PollingProgress(text, snapshots, wait_clock), snapshots, scheduler, waiting, budgets.tasks)

    def hire(addr: str) -> None:
        budgets.agent(addr, False)
        pauses.agent(addr)

    def delegate(sender: str, to: str, title: str, runs_given: int) -> Message:
        return budgets.post(Message(sender=sender, to=to, type="task", title=title, body="goal", budget=runs_given))

    def answer(task: Message, status: str, body: str, returned: int) -> Message:
        return budgets.post(
            Message(sender=task.to, to=task.sender, type="result", title=f"re: {task.title}", body=body, reply_to=task.id, status=status, budget=returned),
        )

    def write(sender: str, to: str, title: str, body: str, runs_given: int) -> Message:
        return budgets.post(Message(sender=sender, to=to, type="note", title=title, body=body, budget=runs_given))

    def retire(addr: str) -> None:
        registry.archive(addr, "20260101T000000")

    def use_run(addr: str) -> None:
        budgets.clock.advance(1)
        runs.add_agent(addr)
        runs.put_log(addr, f"{budgets.clock.now():{STAMP}}.log", "# run\n")
        if fixed is not None:
            fixed.spend(addr)

    return ProgressWorld(
        reporter=reporter, text=text, snapshots=snapshots, mail=budgets.mail, tasks=budgets.tasks, agents=budgets.agents, pauses=pauses.store,
        runnable=runnable, runs=runs.reader, layout=layout, clock=wait_clock, history=history, totals=totals, queue=queue, scheduler=scheduler,
        waiting=waiting, activity=team_activity, hire=hire, retire=retire, delegate=delegate,
        answer=answer, write=write, use_run=use_run, begin_run=budgets.begin_run, end_run=budgets.end_run, pause=pauses.store.pause,
        advance=budgets.clock.advance,
    )


def fs_world(tmp_path: Path) -> ProgressWorld:
    """The reporter over an organization directory (the real derived budget, the real files for the last activity)."""
    budgets = fs_budget_world(tmp_path)
    return _world(
        tmp_path, budgets, fs_runs(tmp_path), fs_pauses(tmp_path), fs_agents(tmp_path).registry, FsTeamActivity, ScriptedClock(budgets.clock),
    )


def memory_world(tmp_path: Path) -> ProgressWorld:
    """The reporter over the in-memory mailboxes, run logs and flags (budgets are numbers; nothing is known about the last activity)."""
    budgets = memory_budget_world(tmp_path)
    box = budgets.mail
    assert isinstance(box, MemoryMailbox)
    return _world(tmp_path, budgets, memory_runs(tmp_path), memory_pauses(tmp_path), box.agents, lambda layout: FixedTeamActivity(), ScriptedClock(budgets.clock))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    ProgressReporter: [fs_world, memory_world],
}
