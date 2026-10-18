"""Creating the skeleton of a new organization on disk."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..settings import OrgDocumentStore
from ..snapshots import IgnoreList, OrgSnapshotter
from ..templates import DocumentTemplates
from .api import OrgInitializer


class FsOrgInitializer(OrgInitializer):
    """Writes ``ORG.md`` through the document store, the ``.gitignore`` and the repository through the snapshot ports, and makes the
    directories of the skeleton itself."""

    def __init__(self, documents: OrgDocumentStore, templates: DocumentTemplates, snapshotter: OrgSnapshotter, ignore_list: IgnoreList) -> None:
        self._documents = documents
        self._templates = templates
        self._snapshotter = snapshotter
        self._ignore_list = ignore_list

    def init(self, root: Path, mission: str | None = None, config: Mapping[str, object] | None = None) -> None:
        raise NotImplementedError
