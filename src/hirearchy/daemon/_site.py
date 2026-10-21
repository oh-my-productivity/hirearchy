"""Getting the organization ready for a scheduler, and the environment the scheduler gets."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..kernel import Clock, Environment, OrgLayout
from ..snapshots import IgnoreList
from ._files import log_of
from ._ports import LaunchEnvironment, LaunchSite
from .api import ExitMarker


class RuntimeLaunchSite(LaunchSite):
    def __init__(self, layout: OrgLayout, ignore: IgnoreList, marker: ExitMarker, clock: Clock) -> None:
        self._layout = layout
        self._ignore = ignore
        self._marker = marker
        self._clock = clock

    def directory(self) -> Path:
        return self._layout.root

    def prepare(self) -> Path:
        self._layout.runtime_dir().mkdir(exist_ok=True)
        self._ignore.ensure_runtime_files()
        self._marker.clear()
        return log_of(self._layout)

    def announce(self, log: Path, argv: Sequence[str]) -> None:
        with open(log, "ab") as out:
            out.write(f"\n# --- scheduler started {self._clock.now():%Y-%m-%d %H:%M:%SZ}: {' '.join(argv)}\n".encode())


class ScrubbedLaunchEnvironment(LaunchEnvironment):
    def __init__(self, layout: OrgLayout, environment: Environment) -> None:
        self._layout = layout
        self._environment = environment

    def variables(self) -> dict[str, str]:
        env = {**self._environment.variables(), "ORG_ROOT": str(self._layout.root), "PYTHONUNBUFFERED": "1"}
        for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
            env.pop(var, None)
        return env
