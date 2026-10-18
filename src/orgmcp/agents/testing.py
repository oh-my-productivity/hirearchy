"""RED skeleton of the in-memory registry and of the registry the contract suites iterate over (step A-agents)."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import JsonObject, OrgPaths
from ..kernel.testing import fs_atomic_writer, system_clock
from ._caching import CachingAgentDirectory, FsCharterStamps, FsDirectoryProbe, LenientCharterReader
from ._charters import FsCharterReader
from ._directory import FsAgentDirectory
from ._registry import FsAgentRegistry
from ._retired import ArchiveFiles, FsRetiredArchive, OsArchiveFiles
from ._tree import TreeDirectory
from .api import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive, RetiredTree


class MemoryAgents(TreeDirectory, CharterReader, AgentRegistry, RetiredArchive):
    """An organization's agent files kept in memory: all four ports at once."""

    root: Path

    def __init__(self) -> None:
        raise NotImplementedError("red: the in-memory registry is not written yet")

    def put(self, path: str, text: str) -> None:
        raise NotImplementedError

    def put_dir(self, path: str) -> None:
        raise NotImplementedError

    def read(self, path: str) -> str | None:
        raise NotImplementedError

    def listing(self, path: str) -> list[str] | None:
        raise NotImplementedError

    def exists(self, addr: str) -> bool:
        raise NotImplementedError

    def children(self, addr: str) -> list[str]:
        raise NotImplementedError

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        raise NotImplementedError

    def memory(self, addr: str) -> str:
        raise NotImplementedError

    def create(self, addr: str, meta: Mapping[str, object], charter_text: str) -> None:
        raise NotImplementedError

    def rewrite_charter(self, addr: str, text: str) -> None:
        raise NotImplementedError

    def archive(self, addr: str, stamp: str) -> str:
        raise NotImplementedError

    def trees(self) -> list[RetiredTree]:
        raise NotImplementedError

    def run_count(self) -> int:
        raise NotImplementedError

    def unspent_budget(self, tree: RetiredTree) -> int:
        raise NotImplementedError


class MemoryArchiveFiles(ArchiveFiles):
    """The file tree of a ``MemoryAgents`` as the retired archive reads it."""

    def __init__(self, agents: MemoryAgents) -> None:
        raise NotImplementedError("red: the in-memory registry is not written yet")

    def walk(self, top: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
        raise NotImplementedError

    def listdir(self, path: Path) -> list[str]:
        raise NotImplementedError

    def is_dir(self, path: Path) -> bool:
        raise NotImplementedError

    def read_text(self, path: Path) -> str:
        raise NotImplementedError


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class AgentsHarness:
    """The four ports over one organization, and the means to prepare and inspect its files behind their back.

    Paths are relative to the organization (``""`` is the organization itself) and use ``/``.
    """

    directory: AgentDirectory
    charters: CharterReader
    registry: AgentRegistry
    archive: RetiredArchive
    put: Callable[[str, str], None]  # a file with this text (parents are created)
    put_dir: Callable[[str], None]  # an empty directory (parents are created)
    read: Callable[[str], str | None]  # the text of a file, None when there is none
    listing: Callable[[str], list[str] | None]  # the sorted entry names of a directory, None when there is none
    problems: MutableMapping[str, str]  # what a lenient charter reader reports (empty and unused for the others)
    lenient: bool = False  # the charter reader answers ``({"role": "?"}, "")`` for a charter it cannot read


def _disk(root: Path) -> tuple[
    Callable[[str, str], None], Callable[[str], None], Callable[[str], str | None], Callable[[str], list[str] | None]
]:
    def put(path: str, text: str) -> None:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def put_dir(path: str) -> None:
        (root / path).mkdir(parents=True, exist_ok=True)

    def read(path: str) -> str | None:
        target = root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    def listing(path: str) -> list[str] | None:
        target = root / path
        return sorted(os.listdir(target)) if target.is_dir() else None

    return put, put_dir, read, listing


def fs_agents(tmp_path: Path) -> AgentsHarness:
    paths = OrgPaths(tmp_path)
    put, put_dir, read, listing = _disk(tmp_path)
    return AgentsHarness(
        FsAgentDirectory(paths),
        FsCharterReader(paths),
        FsAgentRegistry(paths, fs_atomic_writer(tmp_path).writer),
        FsRetiredArchive(paths, OsArchiveFiles()),
        put, put_dir, read, listing, {},
    )


def memory_agents(tmp_path: Path) -> AgentsHarness:
    raise NotImplementedError("red: the in-memory registry is not written yet")


def caching_agents(tmp_path: Path) -> AgentsHarness:
    paths, base = OrgPaths(tmp_path), fs_agents(tmp_path)
    directory = CachingAgentDirectory(FsAgentDirectory(paths), FsDirectoryProbe(paths), system_clock(tmp_path))
    return AgentsHarness(directory, base.charters, base.registry, base.archive, base.put, base.put_dir, base.read, base.listing, {})


def lenient_agents(tmp_path: Path) -> AgentsHarness:
    paths, base = OrgPaths(tmp_path), fs_agents(tmp_path)
    problems: dict[str, str] = {}
    charters = LenientCharterReader(FsCharterReader(paths), FsCharterStamps(paths), problems)
    return AgentsHarness(
        base.directory, charters, base.registry, base.archive, base.put, base.put_dir, base.read, base.listing, problems, True
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    AgentDirectory: [fs_agents, memory_agents, caching_agents],
    CharterReader: [fs_agents, memory_agents, lenient_agents],
    AgentRegistry: [fs_agents, memory_agents],
    RetiredArchive: [fs_agents, memory_agents],
}
