"""``CachingOrgSettings``: the settings of ORG.md parsed once per change; a broken ORG.md means the defaults, and is reported."""

from __future__ import annotations

from collections.abc import MutableMapping

from ..kernel import JsonObject
from ._config import DEFAULT_CONFIG, config_default_model, config_message_cap, config_number
from ._stamp import OrgDocumentStamp
from .api import OrgSettings

PROBLEM_KEY = "ORG.md"  # the key under which a broken ORG.md is reported (the path relative to the organization)


class CachingOrgSettings(OrgSettings):
    def __init__(self, inner: OrgSettings, stamps: OrgDocumentStamp, problems: MutableMapping[str, str]) -> None:
        self._inner = inner
        self._stamps = stamps
        self._problems = problems
        self._cached: tuple[tuple[int, int], JsonObject] | None = None

    def config(self) -> JsonObject:
        try:
            stamp = self._stamps.stamp()
            if self._cached is not None and self._cached[0] == stamp:
                return self._cached[1]
            config = self._inner.config()
            self._cached = (stamp, config)
            self._problems.pop(PROBLEM_KEY, None)
            return config
        except Exception as exc:  # noqa: BLE001 - a dashboard keeps going; the problem is listed instead
            self._problems[PROBLEM_KEY] = type(exc).__name__
            return dict(DEFAULT_CONFIG)

    def rules(self) -> str:
        return self._inner.rules()

    def default_model(self) -> str:
        return config_default_model(self.config())

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        return config_number(self.config(), key, kind)

    def message_cap(self) -> int:
        return config_message_cap(self.config())
