"""``SettingsHealthThresholds``: the numbers where the flags start, from ORG.md over the defaults."""

from __future__ import annotations

from ._ports import ConfigSource
from .api import HealthThresholds


class SettingsHealthThresholds(HealthThresholds):
    def __init__(self, settings: ConfigSource) -> None:
        pass  # red: C-health

    def thresholds(self) -> dict[str, float]:
        raise NotImplementedError("red: C-health")
