"""The settings of ORG.md for the quality view's thresholds (design 12.5): ``settings.readable_config`` behind ``progress``'s own port."""

from __future__ import annotations

from ..kernel import JsonObject
from ..progress._ports import ConfigSource
from ..settings import OrgSettings, readable_config


class ReadableOrgConfig(ConfigSource):
    def __init__(self, settings: OrgSettings) -> None:
        self._settings = settings

    def config(self) -> JsonObject:
        return readable_config(self._settings)
