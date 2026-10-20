"""``SettingsHealthThresholds``: the numbers where the flags start, from ORG.md over the defaults."""

from __future__ import annotations

from ..settings import finite_number
from ._ports import ConfigSource
from .api import HEALTH_DEFAULTS, HealthThresholds


class SettingsHealthThresholds(HealthThresholds):
    def __init__(self, settings: ConfigSource) -> None:
        self._settings = settings

    def thresholds(self) -> dict[str, float]:
        custom = self._settings.config().get("health")
        merged = {**HEALTH_DEFAULTS, **(custom if isinstance(custom, dict) else {})}
        for key, default in HEALTH_DEFAULTS.items():
            number = finite_number(merged[key])
            merged[key] = default if number is None else number
        return merged
