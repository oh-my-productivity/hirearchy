"""The harnesses of the contract suite of ``RulesUpgrader`` and the registry it iterates over.

``TemplateRulesUpgrader`` runs over an ORG.md in memory with the in-memory git, and over an ORG.md on disk with the real ``git`` program
(the public harnesses of ``settings`` and ``snapshots``): the fast stand-in for consumers' tests and the real thing pass the same suite
(``tests/test_contract_rules_upgrader.py``). The composition root's own wiring runs it too (``app/tests/test_wire_upgrade.py``).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..settings import OrgDocumentStore
from ..settings.testing import MemoryOrgSettings, fs_org_document_store
from ..snapshots.testing import real_snapshotter, recording_snapshotter
from ..templates.testing import static_document_templates
from ._upgrader import TemplateRulesUpgrader
from .api import RulesUpgrader


@dataclass(frozen=True)
class UpgradeHarness:
    upgrader: RulesUpgrader
    put: Callable[[str], None]  # ORG.md becomes this text (no commit)
    stored: Callable[[], str | None]  # the text of ORG.md, None when there is none
    commits: Callable[[], list[str]]  # the subjects of the commits that were made, oldest first


class TouchingDocuments(OrgDocumentStore):
    """ORG.md in memory that tells the in-memory git about every write, as a real file would."""

    def __init__(self, inner: MemoryOrgSettings, touch: Callable[[str], None]) -> None:
        self._inner = inner
        self._touch = touch

    def exists(self) -> bool:
        return self._inner.exists()

    def read_raw(self) -> str:
        return self._inner.read_raw()

    def write_raw(self, text: str) -> None:
        self._inner.write_raw(text)
        self._touch("ORG.md")


def template_upgrader_over_memory_ports(tmp_path: Path) -> UpgradeHarness:
    git, memory = recording_snapshotter(tmp_path), MemoryOrgSettings()
    git.make_repository()
    documents = TouchingDocuments(memory, git.change)
    return UpgradeHarness(
        TemplateRulesUpgrader(documents, static_document_templates(), git.snapshotter), memory.set_text, lambda: memory.text,
        lambda: [commit.message for commit in git.commits()],
    )


def template_upgrader_over_disk_and_git(tmp_path: Path) -> UpgradeHarness:
    git = real_snapshotter(tmp_path)
    git.make_repository()
    disk = fs_org_document_store(git.root)
    return UpgradeHarness(
        TemplateRulesUpgrader(disk.store, static_document_templates(), git.snapshotter), disk.put, disk.stored,
        lambda: [commit.message for commit in git.commits()],
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    RulesUpgrader: [template_upgrader_over_memory_ports, template_upgrader_over_disk_and_git],
}
