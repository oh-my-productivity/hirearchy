"""The binding of a server to its organization: the one root path it is bound to, and the organization there once it exists."""
from __future__ import annotations
from pathlib import Path
from ..kernel import OrgError
from ._instructions import DS_STORE
from ._ports import BindingFactory, OrgOpener, OrgPorts
from .api import OrgBindingPort

class OrgBinding(OrgBindingPort):
    """``get()`` is the lazily resolved accessor every tool uses: it returns the ports of the organization or raises a clear ``OrgError`` while
    none exists yet. ``root`` is None only when ORG_ROOT is unset and no organization was found from the working directory;
    ``create(path=...)`` then binds it, once."""

    def __init__(self, root: Path | None, opener: OrgOpener, ports: OrgPorts | None=None, pinned: bool=False) -> None:
        raise NotImplementedError('red: D-mcp')

    @property
    def root(self) -> Path | None:
        raise NotImplementedError('red: D-mcp')

    @property
    def pinned(self) -> bool:
        raise NotImplementedError('red: D-mcp')

    def peek(self) -> OrgPorts | None:
        """The organization if it exists (now), else None."""
        raise NotImplementedError('red: D-mcp')

    def get(self) -> OrgPorts:
        raise NotImplementedError('red: D-mcp')

    def location(self) -> Path | None:
        raise NotImplementedError('red: D-mcp')

    def missing_message(self) -> str:
        raise NotImplementedError('red: D-mcp')

    def _blocked(self) -> bool:
        raise NotImplementedError('red: D-mcp')

    def create(self, mission: str, default_model: str | None=None, path: str | None=None) -> OrgPorts:
        raise NotImplementedError('red: D-mcp')

class OpenerBindings(BindingFactory):
    """The bindings of one process: each over the same opener."""

    def __init__(self, opener: OrgOpener) -> None:
        raise NotImplementedError('red: D-mcp')

    def bind(self, root: Path | None, ports: OrgPorts | None=None, pinned: bool=False) -> OrgBinding:
        raise NotImplementedError('red: D-mcp')

def _entries(directory: Path) -> list[str]:
    try:
        return sorted((p.name for p in directory.iterdir() if p.name != DS_STORE))
    except OSError:
        return []
