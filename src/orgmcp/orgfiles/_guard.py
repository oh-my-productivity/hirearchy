"""The write guard: which paths an agent may write, and the names it may not."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..agents import AgentDirectory
from ..kernel import OrgLayout
from .api import OrgFileStore

_FOLDED_RUNTIME_NAMES: set[str] = {"?"}  # skeleton
_EXACT_FILES: dict[str, str] = {"?": "?"}  # skeleton


def _fold(name: str) -> str:
    """Key under which two file names count as the same name on *some* filesystem."""
    raise NotImplementedError


def case_twin(names: Iterable[str], name: str) -> str | None:
    """The entry of ``names`` that equals ``name`` except for case, if there is one (``None`` when ``name`` itself is there)."""
    raise NotImplementedError


@runtime_checkable
class WriteGuard(Protocol):
    def resolve(self, actor: str, path: str) -> Path:
        """The path ``actor`` may write for ``path``; ``OrgError`` with the reason otherwise."""
        ...


class PathGuard(WriteGuard):
    def __init__(self, layout: OrgLayout, store: OrgFileStore, agents: AgentDirectory) -> None:
        self._layout = layout
        self._store = store
        self._agents = agents

    def resolve(self, actor: str, path: str) -> Path:
        raise NotImplementedError
