"""An in-memory ``strays`` and the registry the contract suites iterate over.

``MemoryStrays`` is both ports over charters, a ledger and a table of modification times kept in memory. The real classes and the fake pass
the same contract suites (``tests/test_contract_*.py``), so a consumer's unit test may use the fake instead of workspaces on disk.
``StraysHarness`` is what a test gets: the two ports, and the means to prepare the workspace and the ledger behind their back.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..access.testing import StaticAccess, charters_on_disk
from ..agents.testing import fs_agents
from ..kernel import JsonObject, OrgPaths
from ..kernel.testing import MemoryLedgerStore, fs_ledger_store
from ._ports import FsMtimeReader, MtimeReader
from ._probe import WorkspaceStrayProbe
from ._registry import LedgerStrayRegistry
from .api import StrayProbe, StrayRegistry


class MemoryMtimes(MtimeReader):
    """Modification times kept in a table: ``set`` makes a path exist."""

    def __init__(self) -> None:
        self.times: dict[Path, float] = {}

    def set(self, path: Path, mtime: float) -> None:
        """``path`` exists, last modified at ``mtime``."""
        self.times[path] = mtime

    def mtime(self, path: Path) -> float | None:
        return self.times.get(path)


class MemoryStrays(StrayProbe, StrayRegistry):
    """Both ports for agents, a ledger and workspace files kept in memory: ``put_agent`` makes an agent, ``touch`` a file or directory."""

    def __init__(self) -> None:
        self.access = StaticAccess()
        self.ledgers = MemoryLedgerStore()
        self.mtimes = MemoryMtimes()
        self._probe = WorkspaceStrayProbe(self.access, self.access.agents, self.mtimes)
        self._registry = LedgerStrayRegistry(self.ledgers, self.access)

    def put_agent(self, addr: str, meta: Mapping[str, object]) -> None:
        """``addr`` becomes an agent whose charter has this frontmatter."""
        self.access.put_agent(addr, meta)

    def touch(self, path: Path, mtime: float) -> None:
        """``path`` (a file or a directory of a workspace) exists, last modified at ``mtime``."""
        self.mtimes.set(path, mtime)

    def probe(self, addr: str) -> dict[str, float]:
        return self._probe.probe(addr)

    def found_since(self, before: Mapping[str, float], after: Mapping[str, float]) -> list[str]:
        return self._probe.found_since(before, after)

    def record(self, addr: str, paths: Sequence[str]) -> None:
        self._registry.record(addr, paths)

    def take_notice(self, addr: str) -> str:
        return self._registry.take_notice(addr)


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class StraysHarness:
    """The two ports over one organization, and the means to prepare its workspace and its ledger behind their back."""

    probe: StrayProbe
    registry: StrayRegistry
    workspace: Path  # a directory below which a test makes workspaces (resolved; it need not exist in memory)
    put_agent: Callable[[str, JsonObject], None]  # ``addr`` becomes an agent whose charter has this frontmatter
    touch: Callable[[Path, float], None]  # a file with this mtime; the directories above it are made
    touch_dir: Callable[[Path, float], None]  # a directory with this mtime; the directories above it are made
    ledger_text: Callable[[], str | None]  # the text of ``.runtime/strays.json``, None when there is none
    put_ledger_text: Callable[[str], None]  # arbitrary text in the ledger (to test damaged ones)


def _utime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def on_disk(tmp_path: Path) -> StraysHarness:
    """The real classes over a workspace and the ledger of an organization directory."""
    access, files, ledgers = charters_on_disk(tmp_path), fs_agents(tmp_path), fs_ledger_store(tmp_path)
    paths = OrgPaths(tmp_path)

    def touch(path: Path, mtime: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        _utime(path, mtime)

    def touch_dir(path: Path, mtime: float) -> None:
        path.mkdir(parents=True, exist_ok=True)
        _utime(path, mtime)

    def ledger_text() -> str | None:
        file = paths.ledger_file("strays")
        return file.read_text(encoding="utf-8") if file.is_file() else None

    return StraysHarness(
        WorkspaceStrayProbe(access.scopes, files.charters, FsMtimeReader()),
        LedgerStrayRegistry(ledgers.store, access.naming),
        (tmp_path / "ws").resolve(),
        access.put_agent,
        touch,
        touch_dir,
        ledger_text,
        lambda raw: ledgers.put_raw("strays", raw),
    )


def memory_strays(tmp_path: Path) -> StraysHarness:
    """The in-memory fake."""
    fake = MemoryStrays()
    return StraysHarness(
        fake,
        fake,
        (tmp_path / "ws").resolve(),
        fake.put_agent,
        fake.touch,
        fake.touch,
        lambda: fake.ledgers.texts.get("strays"),
        lambda raw: fake.ledgers.texts.__setitem__("strays", raw),
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    StrayProbe: [on_disk, memory_strays],
    StrayRegistry: [on_disk, memory_strays],
}
