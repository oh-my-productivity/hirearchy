"""The files of the services on disk: the only writer of ``<owner>/services/**``."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..kernel import ROOT, AtomicWriter, JsonObject, join_frontmatter, norm, split_frontmatter, visible
from ._parse import as_int
from ._protocols import ServicePlaces
from .api import ServiceStore


class FsServiceStore(ServiceStore):
    """Every file is written whole through the atomic writer; the old version of a contract or a playbook is kept in ``history/``."""

    def __init__(self, places: ServicePlaces, writer: AtomicWriter) -> None:
        self._places = places
        self._writer = writer

    def names(self, owner: str) -> list[str]:
        raise NotImplementedError

    def read_contract(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        raise NotImplementedError

    def read_playbook(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        raise NotImplementedError

    def write_contract(self, owner: str, name: str, meta: JsonObject, body: str, archive_version: int | None) -> str:
        raise NotImplementedError

    def write_playbook(
        self, owner: str, name: str, version: int, meta: JsonObject, body: str, archive_version: int | None = None,
    ) -> str:
        raise NotImplementedError

    def retire(self, owner: str, name: str, stamp: str) -> str:
        raise NotImplementedError

    def playbook_history(self, owner: str, name: str) -> list[tuple[int, JsonObject]]:
        raise NotImplementedError

    @staticmethod
    def _read(path: Path) -> tuple[JsonObject, str] | None:
        raise NotImplementedError
