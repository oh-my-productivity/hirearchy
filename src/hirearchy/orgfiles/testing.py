"""An in-memory ``OrgFileStore`` and the registry the contract suites of ``orgfiles`` iterate over.

``MemoryOrgFileStore`` is the files of an organization kept in memory (and a few outside it: the workspaces and inputs agents are granted).
It passes the same contract suite as ``FsOrgFileStore``. The reader and the writer have no fake of their own: they are logic, so the suites
run the real ``GuardedOrgFileReader`` and ``GuardedOrgFileWriter`` twice, over the files and charters on disk and over the in-memory
store with the in-memory agents, access and settings.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..access.testing import DEFAULT_ORG_MD, StaticAccess, charters_on_disk
from ..agents import AgentRegistry
from ..agents.testing import MemoryAgents, fs_agents
from ..kernel import Clock, JsonObject, OrgPaths
from ..kernel.testing import T0, FakeClock, fs_atomic_writer
from ..settings.testing import fs_org_settings
from ._charter_merge import CharterMerger
from ._guard import PathGuard
from ._reader import GuardedOrgFileReader
from ._store import FsOrgFileStore
from ._writer import GuardedOrgFileWriter
from .api import FileKind, OrgFileReader, OrgFileStore, OrgFileWriter


class MemoryOrgFileStore(OrgFileStore):
    """Files kept in memory. The files below ``agents.root`` are the file tree of ``agents`` (so the agents and the store see the same
    files); the others are kept apart, for the workspaces and inputs outside the organization. There are no symbolic links.

    ``write_text`` stamps the file with the time of the clock, ``put`` (behind the store's back) with a fixed one."""

    def __init__(self, agents: MemoryAgents | None = None, clock: Clock | None = None) -> None:
        self.agents = agents if agents is not None else MemoryAgents()
        self.root = self.agents.root
        self._clock = clock if clock is not None else FakeClock()
        self._files: dict[Path, str] = {}  # outside the organization
        self._dirs: set[Path] = set()
        self._times: dict[Path, datetime] = {}

    def _inside(self, path: Path) -> str | None:
        """The key of ``path`` in the tree of the agents (``""`` is the organization itself), None when it is outside."""
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            return None
        return "" if relative == Path(".") else relative.as_posix()

    def _make_dirs(self, path: Path) -> None:
        for directory in (path, *path.parents):
            self._files.pop(directory, None)
            self._dirs.add(directory)

    def resolve(self, path: Path) -> Path:
        return Path(os.path.normpath(path if path.is_absolute() else self.root / path))

    def kind(self, path: Path) -> FileKind:
        key = self._inside(path)
        if key is None:
            return "dir" if path in self._dirs else "file" if path in self._files else "missing"
        return "dir" if key in self.agents.dirs else "file" if key in self.agents.files else "missing"

    def entries(self, path: Path) -> list[str]:
        key = self._inside(path)
        if key is not None:
            return self.agents.listing(key) or []
        return [p.name for p in (*self._dirs, *self._files) if p.parent == path and p != path]

    def read_text(self, path: Path, errors: str = "strict") -> str:
        text = self.read(path)
        if text is not None:
            return text
        if self.kind(path) == "dir":
            raise IsADirectoryError(21, "Is a directory", str(path))
        raise FileNotFoundError(2, "No such file or directory", str(path))

    def modified(self, path: Path) -> datetime:
        if self.kind(path) == "missing":
            raise FileNotFoundError(2, "No such file or directory", str(path))
        return self._times.get(path, T0)

    def write_text(self, path: Path, text: str) -> None:
        self.put(path, text)
        self._times[path] = self._clock.now()

    def put(self, path: Path, text: str) -> None:
        """A file with this text, made behind the store's back (its parent directories too)."""
        self._times[path] = T0
        key = self._inside(path)
        if key is not None:
            self.agents.put(key, text)
            return
        self._make_dirs(path.parent)
        self._dirs.discard(path)
        self._files[path] = text

    def put_dir(self, path: Path) -> None:
        """An empty directory (an existing one keeps its content), made behind the store's back."""
        key = self._inside(path)
        if key is not None:
            self.agents.put_dir(key)
        else:
            self._make_dirs(path)

    def read(self, path: Path) -> str | None:
        """The text of a file, None when there is none."""
        key = self._inside(path)
        return self._files.get(path) if key is None else self.agents.files.get(key)

    def touch(self, path: Path, when: datetime) -> None:
        """The modification time of a file or directory becomes ``when``."""
        if self.kind(path) == "missing":
            raise FileNotFoundError(2, "No such file or directory", str(path))
        self._times[path] = when


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class StoreHarness:
    """A store over one organization directory, and the means to prepare and inspect its files behind its back."""

    store: OrgFileStore
    root: Path  # the organization directory as the store sees it
    outside: Path  # a directory outside the organization
    put: Callable[[Path, str], None]  # a file with this text (absolute path; the directories above it are made)
    put_dir: Callable[[Path], None]  # an empty directory
    read: Callable[[Path], str | None]  # the text of a file, None when there is none
    touch: Callable[[Path, datetime], None]  # the modification time of a path becomes this


@dataclass(frozen=True)
class OrgFilesHarness:
    """The reader and the writer over one organization with agents, and the means to prepare and inspect its files behind their back."""

    reader: OrgFileReader
    writer: OrgFileWriter
    store: OrgFileStore
    root: Path  # the organization directory as the ports see it
    outside: Path  # a directory outside the organization
    add_agent: Callable[[str, JsonObject | None], None]  # ``addr`` becomes an agent: directory skeleton and a charter with ``role: R`` + meta
    put: Callable[[Path, str], None]  # a file with this text (absolute path; the directories above it are made)
    put_dir: Callable[[Path], None]  # an empty directory
    read_back: Callable[[Path], str | None]  # the text of a file, None when there is none
    touch: Callable[[Path, datetime], None]  # the modification time of a path becomes this
    put_org_md: Callable[[str], None]  # ORG.md becomes this text
    registry: AgentRegistry  # the writer of charters (to see which charter rewrites went through it)
    case_sensitive: bool = True  # the files are on a filesystem that tells ``a`` and ``A`` apart


def _disk_ops(
    tmp_path: Path,
) -> tuple[Callable[[Path, str], None], Callable[[Path], None], Callable[[Path], str | None], Callable[[Path, datetime], None]]:
    def put(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def put_dir(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def read(path: Path) -> str | None:
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def touch(path: Path, when: datetime) -> None:
        stamp = when.timestamp()
        os.utime(path, (stamp, stamp))

    return put, put_dir, read, touch


def fs_org_file_store(tmp_path: Path) -> StoreHarness:
    root = (tmp_path / "org").resolve()
    root.mkdir()
    outside = (tmp_path / "elsewhere").resolve()
    outside.mkdir()
    put, put_dir, read, touch = _disk_ops(tmp_path)
    return StoreHarness(FsOrgFileStore(OrgPaths(root), fs_atomic_writer(root).writer), root, outside, put, put_dir, read, touch)


def memory_org_file_store(tmp_path: Path) -> StoreHarness:
    store = MemoryOrgFileStore()
    return StoreHarness(store, store.root, store.root.parent / "elsewhere", store.put, store.put_dir, store.read, store.touch)


def _case_sensitive(directory: Path) -> bool:
    probe = directory / ".case-probe"
    probe.write_text("", encoding="utf-8")
    try:
        return not (directory / ".CASE-PROBE").exists()
    finally:
        probe.unlink()


def guarded_on_disk(tmp_path: Path) -> OrgFilesHarness:
    """The real reader and writer over the files and charters of an organization directory."""
    root = (tmp_path / "org").resolve()
    root.mkdir()
    outside = (tmp_path / "elsewhere").resolve()
    outside.mkdir()
    paths, files, document, access = OrgPaths(root), fs_agents(root), fs_org_settings(root), charters_on_disk(root)
    store = FsOrgFileStore(paths, fs_atomic_writer(root).writer)
    put, put_dir, read, touch = _disk_ops(tmp_path)

    def add_agent(addr: str, meta: JsonObject | None = None) -> None:
        files.registry.create(addr, {"role": "R", **(meta or {})}, "# Role\n\nDo the work.")

    reader = GuardedOrgFileReader(paths, store, files.directory, access.scopes)
    writer = GuardedOrgFileWriter(
        paths, store, PathGuard(paths, store, files.directory), CharterMerger(), files.directory, files.charters, files.registry,
        access.scopes, access.authority, document.settings,
    )
    return OrgFilesHarness(
        reader, writer, store, root, outside, add_agent, put, put_dir, read, touch, document.put, files.registry, _case_sensitive(root)
    )


def guarded_in_memory(tmp_path: Path) -> OrgFilesHarness:
    """The real reader and writer over the in-memory store, agents, access and settings."""
    access = StaticAccess()
    store = MemoryOrgFileStore(access.agents)
    paths = OrgPaths(store.root)
    store.put(store.root / "ORG.md", DEFAULT_ORG_MD)

    def put_org_md(text: str) -> None:
        access.put_config(text)
        store.put(store.root / "ORG.md", text)

    def add_agent(addr: str, meta: JsonObject | None = None) -> None:
        access.agents.create(addr, {"role": "R", **(meta or {})}, "# Role\n\nDo the work.")

    reader = GuardedOrgFileReader(paths, store, access.agents, access)
    writer = GuardedOrgFileWriter(
        paths, store, PathGuard(paths, store, access.agents), CharterMerger(), access.agents, access.agents, access.agents,
        access, access, access.settings,
    )
    return OrgFilesHarness(
        reader, writer, store, store.root, store.root.parent / "elsewhere", add_agent, store.put, store.put_dir, store.read,
        store.touch, put_org_md, access.agents,
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgFileStore: [fs_org_file_store, memory_org_file_store],
    OrgFileReader: [guarded_on_disk, guarded_in_memory],
    OrgFileWriter: [guarded_on_disk, guarded_in_memory],
}
