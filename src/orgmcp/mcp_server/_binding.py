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

    def __init__(self, root: Path | None, opener: OrgOpener, ports: OrgPorts | None = None, pinned: bool = False) -> None:
        self._root = Path(root) if root is not None else None
        self._pinned = pinned  # bound by ORG_ROOT: create_org may not choose another path
        self._opener = opener
        self._ports = ports

    @property
    def root(self) -> Path | None:
        return self._root

    @property
    def pinned(self) -> bool:
        return self._pinned

    def peek(self) -> OrgPorts | None:
        """The organization if it exists (now), else None."""
        if self._ports is None and self._root is not None:
            try:
                self._ports = self._opener.open(self._root)
            except OrgError:
                return None
        return self._ports

    def get(self) -> OrgPorts:
        ports = self.peek()
        if ports is None:
            raise OrgError(self.missing_message())
        return ports

    def location(self) -> Path | None:
        ports = self.peek()
        return ports.root if ports is not None else None

    def missing_message(self) -> str:
        if self._root is None:
            return ("no organization found (ORG_ROOT is not set and none exists in the working directory): "
                    "call create_org(mission=..., path=<absolute path>) first")
        if self._blocked():
            return (f"no organization at {self._root} yet: the directory exists, is not empty and has no ORG.md, so "
                    "create_org will refuse to use it. Point ORG_ROOT at an empty or missing directory")
        return f"no organization at {self._root} yet: call create_org(mission=...) first"

    def _blocked(self) -> bool:
        return self._root is not None and (self._root.is_file() or bool(_entries(self._root)))

    def create(self, mission: str, default_model: str | None = None, path: str | None = None) -> OrgPorts:
        existing = self.peek()
        if existing is not None:
            raise OrgError(f"an organization already exists at {existing.root}; nothing was created. "
                           "It is ready to use: call whoami or status")
        if not (mission or "").strip():
            raise OrgError("mission is required: say in a few sentences what the organization is for")
        wanted = Path(path).expanduser() if path else None
        if wanted is not None and not wanted.is_absolute():
            raise OrgError(f"path must be absolute (got {path!r})")
        wanted = wanted.resolve() if wanted is not None else None
        if self._root is not None:
            if wanted is not None and wanted != self._root:
                raise OrgError(f"this server is bound to {self._root} and cannot create an organization at {wanted}. "
                               "Omit path, or ask the user to register orgmcp with ORG_ROOT set to that path")
            target = self._root
        elif wanted is None:
            raise OrgError("ORG_ROOT is not set and no organization was found here: "
                           "call create_org(mission=..., path=<absolute path>)")
        else:
            target = wanted
            if (target / "ORG.md").is_file():
                raise OrgError(f"an organization already exists at {target}, but this server is not bound to it, "
                               "so it will not be used. Ask the user to register orgmcp with "
                               f"ORG_ROOT={target}")
        if target.is_file():
            raise OrgError(f"{target} is a file, not a directory; nothing was created")
        found = _entries(target)
        if found:
            raise OrgError(f"{target} is not empty ({', '.join(found[:5])}{', ...' if len(found) > 5 else ''}) and is not "
                           "an organization; nothing was created. Use an empty or missing directory")
        try:
            self._opener.initialize(target, mission.strip(), {"default_model": default_model} if default_model else None)
        except OSError as exc:
            raise OrgError(f"could not create the organization at {target}: {exc}") from exc
        ports = self._opener.open(target)
        self._root, self._ports = target, ports
        return ports


class OpenerBindings(BindingFactory):
    """The bindings of one process: each over the same opener."""

    def __init__(self, opener: OrgOpener) -> None:
        self._opener = opener

    def bind(self, root: Path | None, ports: OrgPorts | None = None, pinned: bool = False) -> OrgBinding:
        return OrgBinding(root, self._opener, ports, pinned)


def _entries(directory: Path) -> list[str]:
    try:
        return sorted(p.name for p in directory.iterdir() if p.name != DS_STORE)
    except OSError:  # missing (or unreadable: create will fail with its own error)
        return []
