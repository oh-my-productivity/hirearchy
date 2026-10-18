"""Where things are inside an organization directory: pure path arithmetic (no file access)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ._address import ROOT, norm


@runtime_checkable
class OrgLayout(Protocol):
    root: Path

    def agent_dir(self, addr: str) -> Path:
        """The directory of an agent (the root itself for ``root``)."""
        ...

    def box(self, addr: str, box: str) -> Path:
        """One of an agent's mailbox directories (``inbox``, ``inflight``, ``read``, ``sent``)."""
        ...

    def runtime_dir(self) -> Path:
        """``.runtime``: the runtime's private bookkeeping."""
        ...

    def ledger_file(self, name: str) -> Path:
        """``.runtime/<name>.json``."""
        ...

    def events_dir(self) -> Path:
        """``.runtime/events``."""
        ...

    def retired_dir(self) -> Path:
        """``.retired``: where retired agents are archived."""
        ...

    def rel(self, path: Path) -> str:
        """``path`` relative to the organization root, as text."""
        ...


@dataclass(frozen=True)
class OrgPaths(OrgLayout):
    root: Path

    def agent_dir(self, addr: str) -> Path:
        a = norm(addr)
        return self.root if a == ROOT else self.root / a

    def box(self, addr: str, box: str) -> Path:
        return self.agent_dir(addr) / box

    def runtime_dir(self) -> Path:
        return self.root / ".runtime"

    def ledger_file(self, name: str) -> Path:
        return self.runtime_dir() / f"{name}.json"

    def events_dir(self) -> Path:
        return self.runtime_dir() / "events"

    def retired_dir(self) -> Path:
        return self.root / ".retired"

    def rel(self, path: Path) -> str:
        return str(path.relative_to(self.root))


def inside(p: Path, base: Path) -> bool:
    """``p`` is ``base`` or below it (both already resolved)."""
    return p == base or base in p.parents


def visible(paths: Iterable[Path]) -> list[Path]:
    """The entries that are not hidden (no leading dot), sorted."""
    return sorted(p for p in paths if not p.name.startswith("."))
