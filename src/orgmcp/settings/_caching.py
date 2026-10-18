"""``CachingOrgSettings``: the settings of ORG.md parsed once per change; a broken ORG.md means the defaults, and is reported."""

from __future__ import annotations

from collections.abc import MutableMapping

from ..kernel import JsonObject
from ._stamp import OrgDocumentStamp
from .api import OrgSettings


class CachingOrgSettings(OrgSettings):
    def __init__(self, inner: OrgSettings, stamps: OrgDocumentStamp, problems: MutableMapping[str, str]) -> None:
        self._inner = inner
        self._stamps = stamps
        self._problems = problems

    def config(self) -> JsonObject:
        raise NotImplementedError("red: A-settings")

    def rules(self) -> str:
        raise NotImplementedError("red: A-settings")

    def default_model(self) -> str:
        raise NotImplementedError("red: A-settings")

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        raise NotImplementedError("red: A-settings")

    def message_cap(self) -> int:
        raise NotImplementedError("red: A-settings")
