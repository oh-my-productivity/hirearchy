"""The cases of a service, derived from the mailboxes of its owner and its client and from the run logs."""

from __future__ import annotations

from datetime import datetime

from ..agents import AgentDirectory
from ..kernel import Message, latest_results, msg_time, parent
from ..mail import MailboxReader
from ..services import ServiceCatalog
from ._ports import FeedbackWords, PlaybookTimelines, RunCounter
from .api import Case, CaseHistory, Verdict, lessons_of, version_at


class DerivedCaseHistory(CaseHistory):
    """Reads a service's requests from what its client sent, their results from what the client received, and the client's verdicts from the
    notes it sent; nothing is kept."""

    def __init__(
        self, catalog: ServiceCatalog, agents: AgentDirectory, mail: MailboxReader, words: FeedbackWords, timelines: PlaybookTimelines,
        counter: RunCounter,
    ) -> None:
        self._catalog = catalog
        self._agents = agents
        self._mail = mail
        self._words = words
        self._timelines = timelines
        self._counter = counter

    def playbook_timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        raise NotImplementedError  # red: C-reflection

    def cases(self, owner: str, service: str) -> list[Case]:
        raise NotImplementedError  # red: C-reflection

    def case_of(self, task: Message) -> Case | None:
        raise NotImplementedError  # red: C-reflection
