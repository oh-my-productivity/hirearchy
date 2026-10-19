"""Whether a command line is the scheduler of an organization."""

from __future__ import annotations

from pathlib import Path

from ._ports import SchedulerRecognizer


class SchedulerIdentity(SchedulerRecognizer):
    def recognises(self, command: str, root: Path) -> bool:
        raise NotImplementedError
