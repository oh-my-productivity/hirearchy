"""The tasks root gave and their latest results, and which of them are listed (moved from ``progress._render``/``_listed``)."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..kernel import ROOT, Message, latest_results, stamp_of
from ..mail import MailboxReader
from ._ports import RootTasks

RECENT = timedelta(hours=24)  # without a task id, finished tasks are listed for this long after they finished


class MailRootTasks(RootTasks):
    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def tasks(self) -> list[Message]:
        return [m for m in self._mail.sent(ROOT) if m.type == "task"]

    def latest_results(self) -> dict[str, Message]:
        return latest_results(self._mail.received(ROOT))


def listed(result: Message | None, now: datetime) -> bool:
    """Open and blocked tasks always; finished ones while they are recent."""
    if result is None or result.status == "blocked":
        return True
    finished = stamp_of(result.id)
    return finished is None or now - finished <= RECENT
