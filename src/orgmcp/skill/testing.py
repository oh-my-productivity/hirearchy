"""In-memory fakes of the ``skill`` ports, the harnesses and the registry the contract suites iterate over.

``MemorySkillSource`` and ``MemorySkillStore`` obey the same contract suites as the real ``PackagedSkillSource`` and
``FsSkillStore`` (``tests/test_contract_*.py``), so a consumer's unit test may use them instead of files.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import OrgError
from ._fs import FsSkillStore
from ._install import CopySkillInstaller
from ._source import NOT_FOUND, PackagedSkillSource
from ._target import SKILL_FILE, SKILL_NAME, default_base, target_in
from .api import SkillInstaller, SkillSource, SkillStore

PACKAGED_TEXT = "---\nname: orgmcp\n---\n# the packaged skill\n\nnaïve ✓\n"  # not ASCII on purpose: the file is UTF-8


class MemorySkillSource(SkillSource):
    """The packaged text, or nothing (``read`` then fails as the real source does)."""

    def __init__(self, text: str | None = None) -> None:
        raise NotImplementedError

    def provide(self, text: str) -> None:
        raise NotImplementedError

    def remove(self) -> None:
        raise NotImplementedError

    def read(self) -> str:
        raise NotImplementedError


class MemorySkillStore(SkillStore):
    """Skills directories as a dictionary of files and a set of directories; paths are resolved lexically."""

    def __init__(self, home: Path = Path("/home/user"), cwd: Path = Path("/work")) -> None:
        raise NotImplementedError

    def put_file(self, path: Path, text: str) -> None:
        raise NotImplementedError

    def put_directory(self, path: Path) -> None:
        raise NotImplementedError

    def read_file(self, path: Path) -> str | None:
        raise NotImplementedError

    def target(self, dest: Path | None) -> Path:
        raise NotImplementedError

    def read_existing(self, dest: Path | None) -> str | None:
        raise NotImplementedError

    def write(self, dest: Path | None, text: str) -> str:
        raise NotImplementedError


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class SourceHarness:
    source: SkillSource
    provide: Callable[[str], None]  # the packaged file exists with this text (a second call replaces the text)
    remove: Callable[[], None]  # the packaged file is gone


@dataclass(frozen=True)
class StoreHarness:
    store: SkillStore
    base: Path  # an absolute skills directory (resolved: no symlink on the way)
    home: Path  # the home directory of the store: ``<home>/.kiro/skills`` is its default skills directory
    put_file: Callable[[Path, str], None]  # a file with this text (parents are made)
    put_dir: Callable[[Path], None]  # a directory (parents are made)
    read_file: Callable[[Path], str | None]  # the text of a file, None when there is no file


@dataclass(frozen=True)
class InstallerHarness:
    installer: SkillInstaller
    packaged: str  # the text of the packaged skill
    base: Path
    home: Path
    put_file: Callable[[Path, str], None]
    put_dir: Callable[[Path], None]
    read_file: Callable[[Path], str | None]
    lose_source: Callable[[], None]  # the packaged skill disappears


def _put_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _put_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_file(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def wheel_source(tmp_path: Path) -> SourceHarness:
    """The layout of an installed wheel: ``site/orgmcp/_skill/SKILL.md``."""
    package = tmp_path / "site" / "orgmcp"
    package.mkdir(parents=True)
    return SourceHarness(PackagedSkillSource(package), lambda text: _put_file(package / "_skill" / SKILL_FILE, text),
                         lambda: (package / "_skill" / SKILL_FILE).unlink(missing_ok=True))


def checkout_source(tmp_path: Path) -> SourceHarness:
    """The layout of a source checkout: ``repo/src/orgmcp`` (the package) next to ``repo/skills/orgmcp/SKILL.md``."""
    package = tmp_path / "repo" / "src" / "orgmcp"
    package.mkdir(parents=True)
    shipped = tmp_path / "repo" / "skills" / SKILL_NAME / SKILL_FILE
    return SourceHarness(PackagedSkillSource(package), lambda text: _put_file(shipped, text), lambda: shipped.unlink(missing_ok=True))


def memory_source(tmp_path: Path) -> SourceHarness:
    source = MemorySkillSource()
    return SourceHarness(source, source.provide, source.remove)


def fs_store(tmp_path: Path) -> StoreHarness:
    home = tmp_path / "home"
    home.mkdir()
    base = tmp_path / "skills"
    base.mkdir()
    return StoreHarness(FsSkillStore(lambda: home), base, home, _put_file, _put_dir, _read_file)


def memory_store(tmp_path: Path) -> StoreHarness:
    home = Path("/home/user")
    store = MemorySkillStore(home)
    return StoreHarness(store, Path("/skills"), home, store.put_file, store.put_directory, store.read_file)


def fs_installer(tmp_path: Path) -> InstallerHarness:
    """The real source and the real store over a directory, as ``orgmcp install-skill`` composes them."""
    source = wheel_source(tmp_path)
    source.provide(PACKAGED_TEXT)
    store = fs_store(tmp_path)
    return InstallerHarness(CopySkillInstaller(source.source, store.store), PACKAGED_TEXT, store.base, store.home,
                            _put_file, _put_dir, _read_file, source.remove)


def memory_installer(tmp_path: Path) -> InstallerHarness:
    source = MemorySkillSource(PACKAGED_TEXT)
    store = MemorySkillStore()
    return InstallerHarness(CopySkillInstaller(source, store), PACKAGED_TEXT, Path("/skills"), Path("/home/user"),
                            store.put_file, store.put_directory, store.read_file, source.remove)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    SkillSource: [wheel_source, checkout_source, memory_source],
    SkillStore: [fs_store, memory_store],
    SkillInstaller: [fs_installer, memory_installer],
}

__all__ = [
    "IMPLEMENTATIONS", "InstallerHarness", "MemorySkillSource", "MemorySkillStore", "PACKAGED_TEXT", "SourceHarness", "StoreHarness",
    "SKILL_FILE", "SKILL_NAME", "default_base", "target_in", "OrgError", "NOT_FOUND",
]
