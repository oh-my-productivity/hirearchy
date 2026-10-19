"""The command line that starts the scheduler of an organization."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgLayout
from .api import SchedulerCommand


class VenvSchedulerCommand(SchedulerCommand):
    """``executable`` is the interpreter of the virtual environment the program runs in (``sys.executable``)."""

    def __init__(self, layout: OrgLayout, executable: str) -> None:
        self._layout = layout
        self._executable = executable

    def argv(self, max_runs: int | None, until_done: bool) -> list[str]:
        script = Path(self._executable).with_name("orgmcp")
        base = [str(script)] if script.exists() else [self._executable, "-m", "orgmcp"]
        return [
            *base, "--root", str(self._layout.root), "run",
            *(["--max-runs", str(max_runs)] if max_runs is not None else []),
            *(["--until-done"] if until_done else []),
        ]
