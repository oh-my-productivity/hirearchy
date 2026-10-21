"""ORG.md on disk: the settings, the rules and the raw document (the only writer of the file)."""

from __future__ import annotations

from pathlib import Path

from ..kernel import AtomicWriter, JsonObject, OrgLayout
from ._config import config_default_model, config_message_cap, config_number, parse_config, parse_rules
from .api import OrgDocumentStore, OrgSettings


class FsOrgSettings(OrgSettings, OrgDocumentStore):
    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        self._paths = paths
        self._writer = writer

    def _file(self) -> Path:
        return self._paths.root / "ORG.md"

    def exists(self) -> bool:
        return self._file().is_file()

    def read_raw(self) -> str:
        return self._file().read_text(encoding="utf-8")

    def write_raw(self, text: str) -> None:
        self._writer.write(self._file(), text)

    def config(self) -> JsonObject:
        return parse_config(self.read_raw())

    def rules(self) -> str:
        return parse_rules(self.read_raw())

    def default_model(self) -> str:
        return config_default_model(self.config())

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        return config_number(self.config(), key, kind)

    def message_cap(self) -> int:
        return config_message_cap(self.config())
