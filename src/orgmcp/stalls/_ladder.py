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
        raise NotImplementedError("red: C-stalls")
