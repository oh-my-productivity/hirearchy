"""The runs a team made for a root task, against the runs root put into it (moved from ``progress._runs``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import Message
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._ports import RunCounts


class LogRunCounts(RunCounts):
    def __init__(self, mail: MailboxReader, logs: RunLogReader) -> None:
        self._mail = mail
        self._logs = logs

    def runs_text(self, task: Message, result: Message | None, team: Sequence[str]) -> str:
        raise NotImplementedError("red: C-progress")
