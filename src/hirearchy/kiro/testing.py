"""In-memory fakes of the ``kiro`` ports, the harnesses and the registry the contract suites iterate over.

``MemoryProfileStore`` and ``StaticMcpServerLocator`` obey the same contract suites as the real ``FsProfileStore`` and
``VenvMcpServerLocator`` (``tests/test_contract_*.py``), so a consumer's unit test may use them instead of a ``~/.kiro`` directory.
The confinement policy is a pure function of its arguments: it has one implementation and no fake (``PURE``, rule R8).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from ..access.testing import charters_on_disk
from ..agents.testing import fs_agents
from ..kernel import JsonObject, OrgPaths
from ..kernel.testing import DictEnvironment, fs_atomic_writer
from ._confinement import KiroConfinementPolicy
from ._mcp_locator import VenvMcpServerLocator
from ._profile_document import parse_profile, render_profile
from ._profiles import FsProfileStore
from ._provisioner import OrgProfileProvisioner
from ._runner import KiroRunCommandBuilder
from .api import ConfinementPolicy, McpServerLocator, ProfileProvisioner, ProfileStore, RunCommandBuilder

PURE = {"ConfinementPolicy"}  # a pure function of its arguments: one implementation, no fake

SERVER: dict[str, object] = {"command": "/venv/bin/hirearchy", "args": ["mcp"]}  # what the fake locator answers


class MemoryProfileStore(ProfileStore):
    """Profiles kept as the text they would have on disk (``json.dumps(indent=2)`` and a newline), so an unreadable one can be put there too."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def put_raw(self, name: str, text: str) -> None:
        """A profile file with this exact text (even one that is not JSON)."""
        self.files[name] = text

    def read(self, name: str) -> dict[str, object] | None:
        text = self.files.get(name)
        return None if text is None else parse_profile(text)

    def write(self, name: str, data: Mapping[str, object]) -> None:
        self.files[name] = render_profile(data)


class StaticMcpServerLocator(McpServerLocator):
    """Always the same ``command``/``args`` (a fresh copy on every call)."""

    def __init__(self, command: Mapping[str, object] | None = None) -> None:
        self._command = deepcopy(dict(SERVER if command is None else command))

    def command(self) -> dict[str, object]:
        return deepcopy(self._command)


class CountingProfileStore(ProfileStore):
    """Another store seen from outside: counts what is written to it."""

    def __init__(self, inner: ProfileStore) -> None:
        self._inner = inner
        self.writes: list[str] = []

    def read(self, name: str) -> dict[str, object] | None:
        return self._inner.read(name)

    def write(self, name: str, data: Mapping[str, object]) -> None:
        self.writes.append(name)
        self._inner.write(name, data)


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class StoreHarness:
    store: ProfileStore
    names: Callable[[], list[str]]  # the profiles that exist, sorted
    put_raw: Callable[[str, str], None]  # a profile file with this exact text
    text: Callable[[str], str | None]  # the text of a profile file, None when there is none


@dataclass(frozen=True)
class LocatorHarness:
    locator: McpServerLocator


@dataclass(frozen=True)
class ProvisionerHarness:
    provisioner: ProfileProvisioner  # of the organization at ``root``
    root: Path
    at: Callable[[Path], ProfileProvisioner]  # the same kind of provisioner (same store, same server) for the organization at another root
    names: Callable[[], list[str]]  # the profiles that exist, sorted
    text: Callable[[str], str | None]  # the text of a profile file, None when there is none
    put_raw: Callable[[str, str], None]  # a profile file with this exact text, behind the store's back
    writes: Callable[[], list[str]]  # the names written to the store so far, in order
    server: Mapping[str, object]  # what the locator answers


@dataclass(frozen=True)
class BuilderHarness:
    builder: RunCommandBuilder  # kiro binary ``kiro-cli``
    root: Path
    environment: DictEnvironment
    put_agent: Callable[[str, JsonObject], None]  # ``addr`` becomes an agent whose charter has this frontmatter
    put_config: Callable[[str], None]  # ORG.md becomes this text
    provisioner: ProfileProvisioner  # the one the builder asks (to compare names)
    names: Callable[[], list[str]]  # the profiles that exist, sorted
    profile: Callable[[str], JsonObject | None]  # a profile, parsed


def kiro_confinement(tmp_path: Path) -> ConfinementPolicy:
    return KiroConfinementPolicy()


def _disk_text(directory: Path) -> Callable[[str], str | None]:
    def text(name: str) -> str | None:
        path = directory / f"{name}.json"
        return path.read_text(encoding="utf-8") if path.is_file() else None

    return text


def _disk_names(directory: Path) -> Callable[[], list[str]]:
    return lambda: sorted(p.name for p in directory.iterdir()) if directory.is_dir() else []


def fs_profile_store(tmp_path: Path) -> StoreHarness:
    directory = tmp_path / "home" / ".kiro" / "agents"

    def put_raw(name: str, text: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.json").write_text(text, encoding="utf-8")

    return StoreHarness(FsProfileStore(lambda: directory, fs_atomic_writer(tmp_path).writer), _disk_names(directory), put_raw, _disk_text(directory))


def memory_profile_store(tmp_path: Path) -> StoreHarness:
    fake = MemoryProfileStore()
    return StoreHarness(
        fake, lambda: sorted(f"{name}.json" for name in fake.files), fake.put_raw, lambda name: fake.files.get(name)
    )


def venv_locator(tmp_path: Path) -> LocatorHarness:
    return LocatorHarness(VenvMcpServerLocator(lambda: tmp_path / "venv" / "bin" / "python", tmp_path / "project", lambda name: None))


def static_locator(tmp_path: Path) -> LocatorHarness:
    return LocatorHarness(StaticMcpServerLocator())


def provisioner_on_disk(tmp_path: Path) -> ProvisionerHarness:
    directory = tmp_path / "home" / ".kiro" / "agents"
    store = CountingProfileStore(FsProfileStore(lambda: directory, fs_atomic_writer(tmp_path).writer))
    locator, policy = StaticMcpServerLocator(), KiroConfinementPolicy()

    def at(root: Path) -> ProfileProvisioner:
        return OrgProfileProvisioner(OrgPaths(root), store, policy, locator)

    root = tmp_path / "team" / "org"
    def put_raw(name: str, text: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.json").write_text(text, encoding="utf-8")

    return ProvisionerHarness(at(root), root, at, _disk_names(directory), _disk_text(directory), put_raw, lambda: list(store.writes), SERVER)


def provisioner_in_memory(tmp_path: Path) -> ProvisionerHarness:
    fake = MemoryProfileStore()
    store = CountingProfileStore(fake)
    locator, policy = StaticMcpServerLocator(), KiroConfinementPolicy()

    def at(root: Path) -> ProfileProvisioner:
        return OrgProfileProvisioner(OrgPaths(root), store, policy, locator)

    root = Path("/memory/team/org")
    return ProvisionerHarness(
        at(root), root, at, lambda: sorted(f"{name}.json" for name in fake.files), lambda name: fake.files.get(name), fake.put_raw,
        lambda: list(store.writes), SERVER,
    )


def builder_on_disk(tmp_path: Path) -> BuilderHarness:
    """The real access classes and the real profile store over the files of an organization directory."""
    access, files = charters_on_disk(tmp_path), fs_agents(tmp_path)
    directory = tmp_path.parent / f"{tmp_path.name}-kiro-agents"
    store = FsProfileStore(lambda: directory, fs_atomic_writer(tmp_path).writer)
    paths, environment = OrgPaths(tmp_path), DictEnvironment({"PATH": "/usr/bin", "KEEP": "me"})
    provisioner = OrgProfileProvisioner(paths, store, KiroConfinementPolicy(), StaticMcpServerLocator())
    builder = KiroRunCommandBuilder("kiro-cli", paths, files.charters, access.scopes, access.models, provisioner, environment)
    text = _disk_text(directory)

    def profile(name: str) -> JsonObject | None:
        raw = text(name)
        return None if raw is None else dict(json.loads(raw))

    return BuilderHarness(builder, tmp_path, environment, access.put_agent, access.put_config, provisioner, _disk_names(directory), profile)


def builder_in_memory(tmp_path: Path) -> BuilderHarness:
    from ..access.testing import StaticAccess

    access, store = StaticAccess(), MemoryProfileStore()
    paths, environment = OrgPaths(access.root), DictEnvironment({"PATH": "/usr/bin", "KEEP": "me"})
    provisioner = OrgProfileProvisioner(paths, store, KiroConfinementPolicy(), StaticMcpServerLocator())
    builder = KiroRunCommandBuilder("kiro-cli", paths, access.agents, access, access, provisioner, environment)

    def profile(name: str) -> JsonObject | None:
        raw = store.files.get(name)
        return None if raw is None else dict(json.loads(raw))

    return BuilderHarness(
        builder, access.root, environment, access.put_agent, access.put_config, provisioner,
        lambda: sorted(f"{name}.json" for name in store.files), profile,
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    ConfinementPolicy: [kiro_confinement],
    ProfileStore: [fs_profile_store, memory_profile_store],
    McpServerLocator: [venv_locator, static_locator],
    ProfileProvisioner: [provisioner_on_disk, provisioner_in_memory],
    RunCommandBuilder: [builder_on_disk, builder_in_memory],
}
