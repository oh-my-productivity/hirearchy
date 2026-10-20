"""How many runs a team made between two moments, counted from the run logs."""

from __future__ import annotations

from collections.abc import Sequence

from ._ports import RunCounter, RunLogNames


class LogRunCounter(RunCounter):
    """A run is a log file; a window is given by the first 21 characters of the ids of its first request and its end (the stamp)."""

    def __init__(self, logs: RunLogNames) -> None:
        self._logs = logs

    def runs_between(self, team: Sequence[str], start: str, end: str | None) -> int:
        used = 0
        for addr in team:
            for log in self._logs.files(addr):
                name = f"{log.stem}.log"[:21]
                if name >= start and (end is None or name <= end):
                    used += 1
        return used
