"""In-memory registry of agents and the registry the contract suites iterate over.

``MemoryAgents`` is the agent directory, the charter reader, the registry and the retired archive at once, over a file tree kept
in memory. It passes the same contract suites as the real implementations (``tests/test_contract_*.py``), so a consumer's unit
test may use it instead of directories on disk.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import BOXES, ROOT, JsonObject, OrgPaths, child_addr, join_frontmatter, norm
from ..kernel.testing import fs_atomic_writer, system_clock
from ._caching import CachingAgentDirectory, FsCharterStamps, FsDirectoryProbe, LenientCharterReader
from ._charters import FsCharterReader
from ._directory import FsAgentDirectory
from ._registry import FsAgentRegistry
from ._retired import ArchiveFiles, FsRetiredArchive, OsArchiveFiles
from ._tree import TreeDirectory, parse_charter, root_charter, valid_address
from .api import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive, RetiredTree


def _join(base: str, name: str) -> str:
    """The path of ``name`` in the directory ``base`` (``""`` is the organization itself)."""
    return f"{base}/{name}" if base else name


class MemoryAgents(TreeDirectory, CharterReader, AgentRegistry, RetiredArchive):
    """An organization's agent files kept in memory: all four ports at once.

    The files live in ``files`` and ``dirs`` (paths relative to the organization, ``/`` separated, ``""`` is the organization itself);
    ``put`` and ``put_dir`` prepare them, ``read`` and ``listing`` inspect them. The retired trees are read by the real
    ``FsRetiredArchive`` over the in-memory tree, so the walk rules exist once.
    """

    def __init__(self) -> None:
        self.root = Path("/memory/org")
        self.files: dict[str, str] = {}
        self.dirs: set[str] = {""}
        self._retired = FsRetiredArchive(OrgPaths(self.root), MemoryArchiveFiles(self))

    # ------------------------------------------------------------------ the tree

    def put(self, path: str, text: str) -> None:
        """A file with this text; the directories above it are made."""
        self._mkdirs(path.rpartition("/")[0])
        self.dirs.discard(path)
        self.files[path] = text

    def put_dir(self, path: str) -> None:
        """An empty directory (an existing one keeps its content); the directories above it are made."""
        self._mkdirs(path)

    def read(self, path: str) -> str | None:
        return self.files.get(path)

    def listing(self, path: str) -> list[str] | None:
        """The sorted names in a directory; None when there is no such directory."""
        if path not in self.dirs:
            return None
        prefix = f"{path}/" if path else ""
        return sorted({key[len(prefix) :].split("/", 1)[0] for key in (*self.dirs, *self.files) if key != path and key.startswith(prefix)})

    def _mkdirs(self, path: str) -> None:
        parts = path.split("/") if path else []
        for n in range(len(parts) + 1):
            prefix = "/".join(parts[:n])
            self.files.pop(prefix, None)
            self.dirs.add(prefix)

    @staticmethod
    def _at(addr: str, name: str) -> str:
        """The path of ``name`` in the directory of the agent ``addr``."""
        a = norm(addr)
        return name if a == ROOT else f"{a}/{name}"

    # ------------------------------------------------------------------ AgentDirectory

    def exists(self, addr: str) -> bool:
        a = norm(addr)
        return a == ROOT or (valid_address(a) and f"{a}/AGENT.md" in self.files)

    def children(self, addr: str) -> list[str]:
        a = norm(addr)
        here = "" if a == ROOT else a
        names = self.listing(here) or []
        return [
            child_addr(a, n) for n in names if valid_address(n) and _join(here, n) in self.dirs and _join(_join(here, n), "AGENT.md") in self.files
        ]

    # ------------------------------------------------------------------ CharterReader

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        a = norm(addr)
        if a == ROOT:
            return root_charter()
        path = f"{a}/AGENT.md"
        if path not in self.files:
            raise FileNotFoundError(2, "No such file or directory", path)
        return parse_charter(self.files[path])

    def memory(self, addr: str) -> str:
        return self.files.get(self._at(addr, "MEMORY.md"), "")

    # ------------------------------------------------------------------ AgentRegistry

    def create(self, addr: str, meta: Mapping[str, object], charter_text: str) -> None:
        for sub in (*BOXES, "work", "runs"):
            self.put_dir(self._at(addr, sub))
        self.put(self._at(addr, "MEMORY.md"), "")
        self.put(self._at(addr, "AGENT.md"), join_frontmatter(dict(meta), charter_text))

    def rewrite_charter(self, addr: str, text: str) -> None:
        self.put(self._at(addr, "AGENT.md"), text)

    def archive(self, addr: str, stamp: str, record: Mapping[str, str] | None = None) -> str:
        a = norm(addr)
        if a not in self.dirs:
            raise FileNotFoundError(2, "No such file or directory", a)
        name = f"{a.replace('/', '.')}-{stamp}"
        dest = f".retired/{name}"
        self._mkdirs(".retired")
        if dest in self.dirs:  # like shutil.move: into the directory that is there
            dest = f"{dest}/{a.rsplit('/', 1)[-1]}"

        def moved(path: str) -> str:
            return dest + path[len(a) :] if path == a or path.startswith(f"{a}/") else path

        self.files = {moved(p): text for p, text in self.files.items()}
        self.dirs = {moved(p) for p in self.dirs}
        if record is not None:
            self.put(f"{dest}/RETIRED.md", join_frontmatter(dict(record), ""))
        return name

    # ------------------------------------------------------------------ RetiredArchive

    def trees(self) -> list[RetiredTree]:
        return self._retired.trees()

    def run_count(self) -> int:
        return self._retired.run_count()

    def unspent_budget(self, tree: RetiredTree) -> int:
        return self._retired.unspent_budget(tree)

    def credited(self) -> int:
        return self._retired.credited()


class MemoryArchiveFiles(ArchiveFiles):
    """The file tree of a ``MemoryAgents`` as the retired archive reads it (absolute paths below its ``root``)."""

    def __init__(self, agents: MemoryAgents) -> None:
        self._agents = agents

    def _key(self, path: Path) -> str | None:
        try:
            key = path.relative_to(self._agents.root).as_posix()
        except ValueError:
            return None
        return "" if key == "." else key

    def _entries(self, key: str) -> tuple[list[str], list[str]]:
        """(directories, files) directly in the directory ``key``, sorted."""
        names = self._agents.listing(key) or []
        return [n for n in names if _join(key, n) in self._agents.dirs], [n for n in names if _join(key, n) in self._agents.files]

    def walk(self, top: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
        key = self._key(top)
        if key is not None and key in self._agents.dirs:
            yield from self._walk(top, key)

    def _walk(self, here: Path, key: str) -> Iterator[tuple[Path, list[str], list[str]]]:
        dirs, files = self._entries(key)
        yield here, dirs, files
        for name in dirs:  # the caller may have pruned the list
            yield from self._walk(here / name, _join(key, name))

    def listdir(self, path: Path) -> list[str]:
        key = self._key(path)
        names = None if key is None else self._agents.listing(key)
        if names is None:
            raise FileNotFoundError(2, "No such file or directory", str(path))
        return names

    def is_dir(self, path: Path) -> bool:
        key = self._key(path)
        return key is not None and key in self._agents.dirs

    def read_text(self, path: Path) -> str:
        key = self._key(path)
        if key is not None and key in self._agents.files:
            return self._agents.files[key]
        raise FileNotFoundError(2, "No such file or directory", str(path))


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
    fake = MemoryAgents()
    return AgentsHarness(fake, fake, fake, fake, fake.put, fake.put_dir, fake.read, fake.listing, {})


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
