"""Creating the skeleton of a new organization on disk."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..kernel import BOXES, OrgError, join_frontmatter
from ..settings import DEFAULT_CONFIG, OrgDocumentStore, config_floor_problem
from ..snapshots import IgnoreList, OrgSnapshotter
from ..templates import DocumentTemplates
from .api import INITIAL_IGNORE_LINES, OrgInitializer

FIRST_COMMIT = "init organization"


class FsOrgInitializer(OrgInitializer):
    """Writes ``ORG.md`` through the document store, the ``.gitignore`` and the repository through the snapshot ports, and makes the
    directories of the skeleton itself."""

    def __init__(self, documents: OrgDocumentStore, templates: DocumentTemplates, snapshotter: OrgSnapshotter, ignore_list: IgnoreList) -> None:
        self._documents = documents
        self._templates = templates
        self._snapshotter = snapshotter
        self._ignore_list = ignore_list

    def init(self, root: Path, mission: str | None = None, config: Mapping[str, object] | None = None) -> None:
        if self._documents.exists():
            raise OrgError(f"already an organization: {root}")
        cfg = {**DEFAULT_CONFIG, **(config or {})}
        problem = config_floor_problem(cfg)  # the org-agent floor (docs/design/org-agent-model-floor.md 3): nothing is made below it
        if problem is not None:
            raise OrgError(f"cannot create the organization: {problem}")
        root.mkdir(parents=True, exist_ok=True)
        self._documents.write_raw(join_frontmatter(cfg, self._templates.org_rules(mission)))
        for box in BOXES:
            (root / box).mkdir(exist_ok=True)
        (root / ".runtime").mkdir(exist_ok=True)
        self._ignore_list.write_initial(INITIAL_IGNORE_LINES)
        self._snapshotter.init_repository()
        self._snapshotter.commit(FIRST_COMMIT)
