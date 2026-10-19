"""The command line that starts the scheduler of an organization."""

from __future__ import annotations

from ..kernel import OrgLayout
from .api import SchedulerCommand


class VenvSchedulerCommand(SchedulerCommand):
    def __init__(self, layout: OrgLayout, executable: str) -> None:
        self._layout = layout
        self._executable = executable

    def argv(self, max_runs: int | None, until_done: bool) -> list[str]:
        raise NotImplementedError
