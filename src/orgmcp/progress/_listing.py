"""The tasks root gave and their latest results, and which of them are listed (moved from ``progress._render``/``_listed``)."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..kernel import Message
from ..mail import MailboxReader
from ._ports import RootTasks

RECENT = timedelta(hours=24)  # without a task id, finished tasks are listed for this long after they finished


class MailRootTasks(RootTasks):
    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def tasks(self) -> list[Message]:
        raise NotImplementedError("red: C-progress")

    def latest_results(self) -> dict[str, Message]:
        raise NotImplementedError("red: C-progress")


def listed(result: Message | None, now: datetime) -> bool:
    """Open and blocked tasks always; finished ones while they are recent."""
    raise NotImplementedError("red: C-progress")
