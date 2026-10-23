"""How many runs a team made between two moments, counted from the run logs."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import credited_stems
from ..mail import MailboxReader
from ._ports import RunCounter, RunLogNames


class LogRunCounter(RunCounter):
    """A run is a log file; a window is given by the first 21 characters of the ids of its first request and its end (the stamp).

    A run that ended on a model-service throttle before any tool effect was given back by a run credit in the agent's received box: it was not
    charged, so it is not counted either (the totals and the overspend warning agree with the budget the agent was charged)."""

    def __init__(self, logs: RunLogNames, mail: MailboxReader) -> None:
        self._logs, self._mail = logs, mail

    def runs_between(self, team: Sequence[str], start: str, end: str | None) -> int:
        used = 0
        for addr in team:
            logs = self._logs.files(addr)
            credited = credited_stems(self._mail.received(addr)) if logs else set()
            for log in logs:
                name = f"{log.stem}.log"[:21]
                if name >= start and (end is None or name <= end) and log.stem not in credited:
                    used += 1
        return used
