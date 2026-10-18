"""Where things are inside an organization directory: pure path arithmetic (no file access)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


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
        raise NotImplementedError("red: K1")

    def box(self, addr: str, box: str) -> Path:
        raise NotImplementedError("red: K1")

    def runtime_dir(self) -> Path:
        raise NotImplementedError("red: K1")

    def ledger_file(self, name: str) -> Path:
        raise NotImplementedError("red: K1")

    def events_dir(self) -> Path:
        raise NotImplementedError("red: K1")

    def retired_dir(self) -> Path:
        raise NotImplementedError("red: K1")

    def rel(self, path: Path) -> str:
        raise NotImplementedError("red: K1")


def inside(p: Path, base: Path) -> bool:
    """``p`` is ``base`` or below it (both already resolved)."""
    raise NotImplementedError("red: K1")


def visible(paths: Iterable[Path]) -> list[Path]:
    """The entries that are not hidden (no leading dot), sorted."""
    raise NotImplementedError("red: K1")
