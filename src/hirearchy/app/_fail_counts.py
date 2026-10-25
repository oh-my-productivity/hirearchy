"""The FAIL counts the quality view shows for a signer, from health's escape counter (design 12.5).

``progress`` may not import ``health``, so the composition root joins them: the re-checks and author rework runs a FAIL cost are health's numbers
(0a 5.5), read here and never counted twice."""

from __future__ import annotations

from ..health._ports import EscapeCounter
from ..progress._ports import FailCounts


class HealthFailCounts(FailCounts):
    def __init__(self, counter: EscapeCounter) -> None:
        self._counter = counter

    def fails(self, addr: str) -> tuple[int, int]:
        counts = self._counter.counts(addr)
        return counts.rechecks, counts.rework_runs
