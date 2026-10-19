"""Getting the organization ready for a scheduler, and the environment the scheduler gets."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..kernel import Clock, Environment, OrgLayout
from ..snapshots import IgnoreList
from ._ports import LaunchEnvironment, LaunchSite
from .api import ExitMarker


class RuntimeLaunchSite(LaunchSite):
    def __init__(self, layout: OrgLayout, ignore: IgnoreList, marker: ExitMarker, clock: Clock) -> None:
        self._layout = layout
        self._ignore = ignore
        self._marker = marker
        self._clock = clock

    def prepare(self) -> Path:
        raise NotImplementedError

    def announce(self, log: Path, argv: Sequence[str]) -> None:
        raise NotImplementedError


class ScrubbedLaunchEnvironment(LaunchEnvironment):
    def __init__(self, layout: OrgLayout, environment: Environment) -> None:
        self._layout = layout
        self._environment = environment

    def variables(self) -> dict[str, str]:
        raise NotImplementedError
