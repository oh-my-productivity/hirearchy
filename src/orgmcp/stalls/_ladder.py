"""``EscalationStallLadder``: remind the assignee of a quiet task, then tell the assigner, then each ancestor up to root (moved from ``Scheduler._check_stalls``)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..eligibility import PauseStore
from ..kernel import Clock, EventSink
from ..mail import MailboxReader
from ..runs import RunLogReader
from ..settings import OrgSettings
from ..templates import Notices
from ._ports import CreationTimes, NudgeRecorder, TaskViews
from .api import NudgeLedger, StallLadder

PROC = "scheduler"  # the process whose events these are: only the scheduler climbs the ladder
ACTOR = "runtime"


class EscalationStallLadder(StallLadder):
    def __init__(
        self,
        clock: Clock,
        settings: OrgSettings,
        agents: AgentDirectory,
        views: TaskViews,
        mailbox: MailboxReader,
        pauses: PauseStore,
        runs: RunLogReader,
        created: CreationTimes,
        nudges: NudgeLedger,
        recorder: NudgeRecorder,
        delivery: MessageDelivery,
        notices: Notices,
        events: EventSink,
    ) -> None:
        self._clock = clock
        self._settings = settings
        self._agents = agents
        self._views = views
        self._mailbox = mailbox
        self._pauses = pauses
        self._runs = runs
        self._created = created
        self._nudges = nudges
        self._recorder = recorder
        self._delivery = delivery
        self._notices = notices
        self._events = events

    def check(self) -> list[str]:
        """Stalled = assignee not running, no unread mail, not paused, not waiting on delegated work, and ``stall_after`` seconds since the latest of:
        the task's creation, the assignee's last run, the previous step. Steps: remind the assignee, then tell the assigner, then each ancestor in
        turn up to root."""
        after, now = self._settings.number("stall_after"), self._clock.time()
        ledger = self._nudges.entries()  # task id -> {"step": last step taken, "at": when}
        kept: dict[str, dict[str, float]] = {}  # entries of tasks that are still open
        lines: list[str] = []
        agents = self._agents.agents()
        self._views.retain(agents)
        for addr in agents:
            tasks = self._views.open_tasks(addr)
            stuck = bool(tasks) and not (
                self._mailbox.has_inflight(addr) or self._mailbox.unread(addr) or self._pauses.paused(addr) or self._views.outstanding(addr)
            )
            for task in tasks:
                last = ledger.get(task.id)
                if last:
                    kept[task.id] = last
                if not stuck:
                    continue
                chain = self._nudges.chain(addr, task)
                step = int(last["step"]) + 1 if last else 0
                if step >= len(chain):  # root has been told: nothing further up
                    continue
                since = max(self._created.of(task), self._runs.last_end(addr), last["at"] if last else 0)
                if now - since < after:
                    continue
                if step == 0:
                    self._delivery.notify(addr, f"reminder: {task.title}", self._notices.nudge(task.id, task.title), trace=task.trace)
                    lines.append(f"{addr}: reminded about open task {task.id}")
                else:
                    self._delivery.notify(
                        chain[step], f"stalled: {task.title}", self._notices.stalled(addr, task.id, task.title, chain[:step]), trace=task.trace,
                    )
                    lines.append(f"{addr}: stalled on {task.id}, told {chain[step]}")
                self._events.emit("stall.nudge", actor=ACTOR, proc=PROC, trace=task.trace, task=task.id, to=chain[step] if step else addr, step=step)
                kept[task.id] = {"step": step, "at": now}
        self._recorder.save(kept)
        return lines
