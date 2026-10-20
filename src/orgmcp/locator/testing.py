"""In-memory fakes of the ``locator`` port, and the registry the contract suite iterates over."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import Environment, OrgError
from ..kernel.testing import DictEnvironment
from ._env import NOT_FOUND, EnvOrgLocator
from .api import OrgLocator


class MemoryOrgLocator(OrgLocator):
    """The same lookup over a set of directories that are organizations (no file is looked at)."""

    def __init__(self, environment: Environment, organizations: set[Path] | None = None) -> None:
        self._environment = environment
        self.organizations = organizations if organizations is not None else set()

    def find_root(self, start: str | Path | None = None) -> Path:
        env = self._environment.get("ORG_ROOT")
        if env:
            return Path(env).expanduser().resolve()
        here = Path(start or self._environment.cwd()).resolve()
        for d in (here, *here.parents):
            if d in self.organizations:
                return d
        if here / "org" in self.organizations:
            return here / "org"
        raise OrgError(NOT_FOUND)


class FixedOrgLocator(OrgLocator):
    """Always finds the same root (for a consumer's test that does not care how it is found)."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def find_root(self, start: str | Path | None = None) -> Path:
        return self._root


@dataclass(frozen=True)
class LocatorHarness:
    locator: OrgLocator
    cwd: Path  # the working directory of the locator (a directory three levels below tmp_path)
    make_org: Callable[[Path], None]  # the directory becomes an organization (it holds ORG.md)
    make_decoy: Callable[[Path], None]  # something named ORG.md that is not a file
    set_env: Callable[[str, str], None]  # define a variable of the locator's environment


def _workdir(tmp_path: Path) -> Path:
    cwd = tmp_path / "a" / "b" / "c"
    cwd.mkdir(parents=True)
    return cwd


def _decoy(path: Path) -> None:
    (path / "ORG.md").mkdir(parents=True, exist_ok=True)


def env_org_locator(tmp_path: Path) -> LocatorHarness:
    cwd = _workdir(tmp_path)
    environment = DictEnvironment(cwd=cwd)

    def make_org(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / "ORG.md").write_text("---\n---\n", encoding="utf-8")

    return LocatorHarness(EnvOrgLocator(environment), cwd, make_org, _decoy, environment.set)


def memory_org_locator(tmp_path: Path) -> LocatorHarness:
    cwd = _workdir(tmp_path)
    environment = DictEnvironment(cwd=cwd)
    locator = MemoryOrgLocator(environment)
    return LocatorHarness(locator, cwd, locator.organizations.add, _decoy, environment.set)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgLocator: [env_org_locator, memory_org_locator],
}
