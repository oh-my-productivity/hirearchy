"""ORG.md on disk: the settings, the rules and the raw document (the only writer of the file)."""

from __future__ import annotations

from ..kernel import AtomicWriter, JsonObject, OrgLayout
from .api import OrgDocumentStore, OrgSettings


class FsOrgSettings(OrgSettings, OrgDocumentStore):
    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        self._paths = paths
        self._writer = writer

    def exists(self) -> bool:
        raise NotImplementedError("red: A-settings")

    def read_raw(self) -> str:
        raise NotImplementedError("red: A-settings")

    def write_raw(self, text: str) -> None:
        raise NotImplementedError("red: A-settings")

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
