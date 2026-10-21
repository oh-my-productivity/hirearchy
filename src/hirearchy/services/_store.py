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
        if norm(owner) == ROOT:
            return []
        directory = self._places.services_dir(owner)
        if not directory.is_dir():
            return []
        return [p.name for p in visible(directory.iterdir()) if p.is_dir() and (p / "SERVICE.md").is_file()]

    def read_contract(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        return self._read(self._places.contract_file(owner, name))

    def read_playbook(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        return self._read(self._places.playbook_file(owner, name))

    def write_contract(self, owner: str, name: str, meta: JsonObject, body: str, archive_version: int | None) -> str:
        path = self._places.contract_file(owner, name)
        if archive_version is not None:
            self._writer.write(self._places.history_file(owner, name, "SERVICE", archive_version), path.read_text(encoding="utf-8"))
        self._writer.write(path, join_frontmatter(meta, body))
        return self._places.rel(path)

    def write_playbook(
        self, owner: str, name: str, version: int, meta: JsonObject, body: str, archive_version: int | None = None,
    ) -> str:
        path = self._places.playbook_file(owner, name)
        if archive_version is not None:
            self._writer.write(self._places.history_file(owner, name, "PLAYBOOK", archive_version), path.read_text(encoding="utf-8"))
        self._writer.write(path, join_frontmatter(meta, body))
        return self._places.rel(path)

    def retire(self, owner: str, name: str, stamp: str) -> str:
        dest = self._places.retired_dir(owner, name, stamp)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self._places.service_dir(owner, name)), dest)
        return self._places.rel(dest)

    def playbook_history(self, owner: str, name: str) -> list[tuple[int, JsonObject]]:
        directory = self._places.service_dir(owner, name)
        paths = [*sorted((directory / "history").glob("PLAYBOOK.v*.md")), self._places.playbook_file(owner, name)]
        found: list[tuple[int, JsonObject]] = []
        for path in paths:
            if path.is_file():
                meta = split_frontmatter(path.read_text(encoding="utf-8"))[0]
                found.append((as_int(meta.get("version")), meta))
        return found

    @staticmethod
    def _read(path: Path) -> tuple[JsonObject, str] | None:
        if not path.is_file():
            return None
        return split_frontmatter(path.read_text(encoding="utf-8"))
