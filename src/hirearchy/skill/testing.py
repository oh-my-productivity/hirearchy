"""In-memory fakes of the ``skill`` ports, the harnesses and the registry the contract suites iterate over.

``MemorySkillSource`` and ``MemorySkillStore`` obey the same contract suites as the real ``PackagedSkillSource`` and
``FsSkillStore`` (``tests/test_contract_*.py``), so a consumer's unit test may use them instead of files.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import OrgError
from ._fs import NOT_A_FILE, FsSkillStore
from ._install import CopySkillInstaller
from ._source import NOT_FOUND, PackagedSkillSource
from ._target import SKILL_FILE, SKILL_NAME, default_base, target_in
from .api import SkillCheck, SkillInstaller, SkillSource, SkillStore

PACKAGED_TEXT = "---\nname: hirearchy\n---\n# the packaged skill\n\nnaïve ✓\n"  # not ASCII on purpose: the file is UTF-8


class MemorySkillSource(SkillSource):
    """The packaged text, or nothing (``read`` then fails as the real source does)."""

    def __init__(self, text: str | None = None) -> None:
        self._text = text

    def provide(self, text: str) -> None:
        """The packaged file exists with this text."""
        self._text = text

    def remove(self) -> None:
        """The packaged file is gone."""
        self._text = None

    def read(self) -> str:
        if self._text is None:
            raise OrgError(NOT_FOUND)
        return self._text


class MemorySkillStore(SkillStore):
    """Skills directories as a dictionary of files and a set of directories; paths are resolved lexically (no symlinks)."""

    def __init__(self, home: Path = Path("/home/user"), cwd: Path = Path("/work")) -> None:
        self._home = home
        self._cwd = cwd
        self._files: dict[Path, str] = {}
        self._directories: set[Path] = set()

    def put_file(self, path: Path, text: str) -> None:
        """A file with this text (its parents are directories)."""
        self._files[path] = text

    def put_directory(self, path: Path) -> None:
        """A directory (its parents are directories too)."""
        self._directories.add(path)

    def read_file(self, path: Path) -> str | None:
        """The text of a file; ``None`` when ``path`` is no file."""
        return self._files.get(path)

    def _is_directory(self, path: Path) -> bool:
        return path in self._directories or any(path in file.parents for file in self._files) or any(
            path in directory.parents for directory in self._directories)

    def _base(self, dest: Path | None) -> Path:
        base = default_base(self._home) if dest is None else dest
        if base.parts[:1] == ("~",):
            base = self._home.joinpath(*base.parts[1:])
        return Path(os.path.normpath(base if base.is_absolute() else self._cwd / base))

    def target(self, dest: Path | None) -> Path:
        return target_in(self._base(dest))

    def read_existing(self, dest: Path | None) -> str | None:
        target = self.target(dest)
        if target in self._files:
            return self._files[target]
        if self._is_directory(target):
            raise OrgError(NOT_A_FILE.format(target=target))
        return None

    def write(self, dest: Path | None, text: str) -> str:
        target = self.target(dest)
        if self._is_directory(target):
            raise IsADirectoryError(str(target))
        self._files[target] = text
        return str(target)


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
    """The layout of an installed wheel: ``site/hirearchy/_skill/SKILL.md``."""
    package = tmp_path / "site" / "hirearchy"
    package.mkdir(parents=True)
    return SourceHarness(PackagedSkillSource(package), lambda text: _put_file(package / "_skill" / SKILL_FILE, text),
                         lambda: (package / "_skill" / SKILL_FILE).unlink(missing_ok=True))


def checkout_source(tmp_path: Path) -> SourceHarness:
    """The layout of a source checkout: ``repo/src/hirearchy`` (the package) next to ``repo/skills/hirearchy/SKILL.md``."""
    package = tmp_path / "repo" / "src" / "hirearchy"
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
    """The real source and the real store over a directory, as ``hirearchy install-skill`` composes them."""
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
    SkillCheck: [fs_installer, memory_installer],
}
