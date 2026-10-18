"""An in-memory initializer, the harnesses of the contract suite, and the registry it iterates over.

``MemoryOrgInitializer`` is an ``OrgInitializer`` that keeps the organizations it made in memory. The real ``FsOrgInitializer`` runs over
the in-memory ports of ``settings`` and ``snapshots`` (the real ports are assembled by the composition root: ``app/tests/test_wire_bootstrap.py``
runs the same suite over them). Every one of them passes the contract suite (``tests/test_contract_org_initializer.py``), so a consumer's
unit test may use the fake instead of a directory and the ``git`` program.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..kernel import BOXES, OrgError, join_frontmatter
from ..settings import DEFAULT_CONFIG
from ..settings.testing import MemoryOrgSettings
from ..snapshots import OrgSnapshotter
from ..snapshots.testing import MemoryIgnoreList
from ..templates import DocumentTemplates
from ..templates.testing import static_document_templates
from ._initializer import FsOrgInitializer
from .api import INITIAL_IGNORE_LINES, OrgInitializer

FIRST_COMMIT = "init organization"


@dataclass
class MemoryOrganization:
    """What a made organization consists of."""

    org_md: str
    directories: frozenset[str]
    gitignore: str
    repository: bool
    commits: list[str] = field(default_factory=list)


class MemoryOrgInitializer(OrgInitializer):
    """Organizations in memory, by root. ``git_available=False``: the program does not exist, so no repository and no commit."""

    def __init__(self, templates: DocumentTemplates, git_available: bool = True) -> None:
        self._templates = templates
        self._git_available = git_available
        self.organizations: dict[Path, MemoryOrganization] = {}

    def init(self, root: Path, mission: str | None = None, config: Mapping[str, object] | None = None) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class InitHarness:
    initializer: OrgInitializer
    root: Path  # not an organization yet: nothing exists there
    org_md: Callable[[], str | None]  # the text of ORG.md, None when there is none
    directories: Callable[[], list[str]]  # the directories below root (git's own excluded) as "name/", sorted
    gitignore: Callable[[], str | None]  # the text of .gitignore, None when there is none
    commits: Callable[[], list[str]]  # the subjects of the commits that were asked for, oldest first
    has_repository: Callable[[], bool]
    put_org_md: Callable[[str], None]  # an ORG.md that was there before, behind the initializer's back


class JournalSnapshotter(OrgSnapshotter):
    """A snapshotter that makes nothing and remembers what it was asked: ``repository`` after ``init_repository``, the messages of
    ``commit``. ``git_available=False`` is a machine without the git program: no repository, so no commit."""

    def __init__(self, git_available: bool = True) -> None:
        self.git_available = git_available
        self.repository = False
        self.commits: list[str] = []

    def init_repository(self) -> None:
        if self.git_available:
            self.repository = True

    def commit(self, message: str) -> None:
        if self.repository:
            self.commits.append(message)


def directories_below(root: Path) -> list[str]:
    """The directories below ``root`` (git's own excluded) as ``name/``, sorted: what a harness reports as ``directories``."""
    if not root.is_dir():
        return []
    return sorted(f"{p.relative_to(root)}/" for p in root.rglob("*") if p.is_dir() and p.relative_to(root).parts[0] != ".git")


def _ports_harness(tmp_path: Path, git_available: bool) -> InitHarness:
    root = tmp_path / "org"
    settings, ignore, snapshotter = MemoryOrgSettings(), MemoryIgnoreList(), JournalSnapshotter(git_available)
    return InitHarness(
        FsOrgInitializer(settings, static_document_templates(), snapshotter, ignore), root, lambda: settings.text,
        lambda: directories_below(root), lambda: ignore.text, lambda: list(snapshotter.commits), lambda: snapshotter.repository,
        settings.set_text,
    )


def real_initializer_over_memory_ports(tmp_path: Path) -> InitHarness:
    return _ports_harness(tmp_path, True)


def real_initializer_over_memory_ports_without_git(tmp_path: Path) -> InitHarness:
    return _ports_harness(tmp_path, False)


def _memory_harness(tmp_path: Path, git_available: bool) -> InitHarness:
    root = tmp_path / "org"
    initializer = MemoryOrgInitializer(static_document_templates(), git_available)
    nothing = MemoryOrganization("", frozenset(), "", False)

    def made() -> MemoryOrganization | None:
        return initializer.organizations.get(root)

    def put_org_md(text: str) -> None:
        initializer.organizations[root] = MemoryOrganization(text, frozenset(), "", False)

    def org_md() -> str | None:
        return org.org_md if (org := made()) else None

    def gitignore() -> str | None:
        return (made() or nothing).gitignore or None

    return InitHarness(
        initializer, root, org_md, lambda: sorted((made() or nothing).directories), gitignore,
        lambda: list((made() or nothing).commits), lambda: (made() or nothing).repository, put_org_md,
    )


def memory_initializer(tmp_path: Path) -> InitHarness:
    return _memory_harness(tmp_path, True)


def memory_initializer_without_git(tmp_path: Path) -> InitHarness:
    return _memory_harness(tmp_path, False)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgInitializer: [real_initializer_over_memory_ports, memory_initializer],
}

# The same initializer when the git program does not exist.
WITHOUT_GIT: Sequence[Callable[[Path], InitHarness]] = [real_initializer_over_memory_ports_without_git, memory_initializer_without_git]
