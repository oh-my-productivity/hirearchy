"""In-memory fakes of the ``locator`` port, and the registry the contract suite iterates over."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import Environment
from ._env import EnvOrgLocator
from .api import OrgLocator


class MemoryOrgLocator(OrgLocator):
    """The same lookup over a set of directories that are organizations (no file is looked at)."""

    def __init__(self, environment: Environment, organizations: set[Path] | None = None) -> None:
        self._environment = environment
        self.organizations = organizations if organizations is not None else set()

    def find_root(self, start: Path | None = None) -> Path:
        raise NotImplementedError("red: A-settings")


class FixedOrgLocator(OrgLocator):
    """Always finds the same root (for a consumer's test that does not care how it is found)."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def find_root(self, start: Path | None = None) -> Path:
        raise NotImplementedError("red: A-settings")


@dataclass(frozen=True)
class LocatorHarness:
    locator: OrgLocator
    cwd: Path  # the working directory of the locator (a directory three levels below tmp_path)
    make_org: Callable[[Path], None]  # the directory becomes an organization (it holds ORG.md)
    make_decoy: Callable[[Path], None]  # something named ORG.md that is not a file
    set_env: Callable[[str, str], None]  # define a variable of the locator's environment


def env_org_locator(tmp_path: Path) -> LocatorHarness:
    raise NotImplementedError("red: A-settings")


def memory_org_locator(tmp_path: Path) -> LocatorHarness:
    raise NotImplementedError("red: A-settings")


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgLocator: [env_org_locator, memory_org_locator],
}
