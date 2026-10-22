"""In-memory fakes of the ``kiro`` ports, the harnesses and the registry the contract suites iterate over.

``MemoryProfileStore`` and ``StaticMcpServerLocator`` obey the same contract suites as the real ``FsProfileStore`` and
``VenvMcpServerLocator`` (``tests/test_contract_*.py``), so a consumer's unit test may use them instead of a ``~/.kiro`` directory.
The confinement policy is a pure function of its arguments: it has one implementation and no fake (``PURE``, rule R8).
"""

from __future__ import annotations

import json
import stat
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from ..access.testing import charters_on_disk
from ..agents.testing import fs_agents
from ..kernel import JsonObject, OrgPaths
from ..kernel.testing import DictEnvironment, fs_atomic_writer, system_clock
from ._cli import SubprocessKiroCli
from ._confinement import KiroConfinementPolicy
from ._mcp_locator import VenvMcpServerLocator
from ._profile_document import parse_profile, render_profile
from ._places import StateDirPlaces
from ._profiles import FsProfileStore
from ._provisioner import OrgProfileProvisioner
from ._readiness import KiroReadiness
from ._runner import KiroRunCommandBuilder
from ._state import FsKiroState
from .api import (
    CliResult, ConfinementPolicy, KiroCli, KiroHomeAudit, KiroPlaces, KiroStateDirs, McpServerLocator, ProfileProvisioner, ProfileStore,
    RunCommandBuilder, RuntimeReadiness,
)

PURE = {"ConfinementPolicy"}  # a pure function of its arguments: one implementation, no fake

SERVER: dict[str, object] = {"command": "/venv/bin/hirearchy", "args": ["mcp"]}  # what the fake locator answers
LAUNCHER = ("/venv/bin/python", "-I", "-S", "/package/kiro/_launch.py")  # what the composition root hands the builder: interpreter, its flags, the script


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


class FixedKiroPlaces(KiroPlaces):
    """Homes, scratch directories and roots below ``base`` (one organization); ``problem`` is what ``problem()`` answers."""

    def __init__(self, base: Path, problem: str | None = None) -> None:
        self._base = base
        self._problem = problem

    def home(self) -> Path:
        return self._base / "kiro-home" / "org"

    def scratch(self, addr: str) -> Path:
        return self._base / "kiro-cwd" / "org" / addr.replace("/", "-")

    def roots(self) -> tuple[Path, Path]:
        return self._base / "kiro-home", self._base / "kiro-cwd"

    def problem(self) -> str | None:
        return self._problem


class MemoryKiroState(KiroStateDirs, KiroHomeAudit):
    """Records ``private_dir`` and ``fresh`` calls; ``plant`` simulates a file a user or an agent left in a home."""

    def __init__(self) -> None:
        self.private: list[Path] = []
        self.fresh_calls: list[Path] = []
        self.planted_files: dict[Path, set[str]] = {}

    def plant(self, home: Path, rel: str) -> None:
        """``rel`` (relative to ``home``) now exists there."""
        self.planted_files.setdefault(home, set()).add(rel)

    def private_dir(self, path: Path) -> None:
        self.private.append(path)

    def fresh(self, path: Path) -> None:
        self.fresh_calls.append(path)

    def planted(self, home: Path) -> list[str]:
        return sorted(self.planted_files.get(home, ()))


class ScriptedKiroCli(KiroCli):
    """Answers by argv from a table (``None``, i.e. "cannot start or overran", for an argv not in it); records every call."""

    def __init__(self, answers: Mapping[tuple[str, ...], CliResult | None]) -> None:
        self._answers = dict(answers)
        self.calls: list[tuple[tuple[str, ...], dict[str, str], float]] = []  # (argv, env, timeout)

    def run(self, argv: Sequence[str], env: Mapping[str, str], timeout: float) -> CliResult | None:
        self.calls.append((tuple(argv), dict(env), timeout))
        return self._answers.get(tuple(argv))


class FixedReadiness(RuntimeReadiness):
    """``check`` answers ``problem`` and ``state_problem`` answers ``state``, whatever the world."""

    def __init__(self, problem: str | None, state: str | None = None) -> None:
        self._problem = problem
        self._state = state

    def state_problem(self) -> str | None:
        return self._state

    def check(self, kiro_bin: str) -> str | None:
        return self._problem


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class PlacesHarness:
    places: KiroPlaces  # a valid world
    broken: KiroPlaces  # the same kind of places in a world with a problem
    base: Path  # a directory below which nothing may be created by computing places


@dataclass(frozen=True)
class CliHarness:
    cli: KiroCli
    succeeds: list[str]  # an argv that exits 0 and prints "hello"
    fails: list[str]  # exits 3 and prints "bad"
    missing: list[str]  # cannot start
    hangs: list[str]  # does not finish


@dataclass(frozen=True)
class ReadinessHarness:
    ready: RuntimeReadiness  # a world in which kiro-cli is ready
    broken: RuntimeReadiness  # a world with a problem (``state_problem`` and ``check`` both answer it)
    kiro_bin: str  # what to pass to ``check``


@dataclass(frozen=True)
class StateHarness:
    dirs: KiroStateDirs
    audit: KiroHomeAudit
    base: Path  # a directory the world may use
    is_empty_dir: Callable[[Path], bool]  # ``fresh`` was the last thing done to it and it is an empty directory
    is_private_dir: Callable[[Path], bool]  # ``private_dir`` made it a directory only its owner can use
    plant: Callable[[Path, str], None]  # ``rel`` now exists below the home


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
    places: KiroPlaces  # where the builder keeps the home and the scratch directories of this organization
    state: StateHarness  # the directories and the audit it asks (``plant`` puts a file into the home)
    launcher: tuple[str, ...]  # what the builder was given to put before the kiro command


def state_dir_places(tmp_path: Path) -> PlacesHarness:
    root = tmp_path / "org"
    home = tmp_path.parent / f"{tmp_path.name}-home"  # outside the org, like the other harnesses
    valid = DictEnvironment({"HIREARCHY_STATE_DIR": str(tmp_path / "state")}, home=home)
    bad = DictEnvironment({"HIREARCHY_STATE_DIR": "relative/state"}, home=home)
    return PlacesHarness(StateDirPlaces(OrgPaths(root), valid, "linux"), StateDirPlaces(OrgPaths(root), bad, "linux"), tmp_path)


def fixed_places(tmp_path: Path) -> PlacesHarness:
    return PlacesHarness(FixedKiroPlaces(tmp_path / "state"), FixedKiroPlaces(tmp_path / "state", "the places are bad"), tmp_path)


def fs_state(tmp_path: Path) -> StateHarness:
    state = FsKiroState(system_clock(tmp_path))

    def plant(home: Path, rel: str) -> None:
        path = home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    return StateHarness(
        state, state, tmp_path,
        lambda p: p.is_dir() and not p.is_symlink() and not any(p.iterdir()),
        lambda p: p.is_dir() and stat.S_IMODE(p.stat().st_mode) == 0o700,
        plant,
    )


def memory_state(tmp_path: Path) -> StateHarness:
    fake = MemoryKiroState()
    return StateHarness(
        fake, fake, tmp_path,
        lambda p: bool(fake.fresh_calls) and fake.fresh_calls[-1] == p,
        lambda p: p in fake.private,
        fake.plant,
    )


def _script(path: Path, body: str) -> list[str]:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return [str(path)]


def subprocess_cli(tmp_path: Path) -> CliHarness:
    return CliHarness(
        SubprocessKiroCli(),
        _script(tmp_path / "succeeds", "echo hello\n"),
        _script(tmp_path / "fails", "echo bad >&2\nexit 3\n"),
        [str(tmp_path / "missing")],
        _script(tmp_path / "hangs", "exec sleep 30\n"),
    )


def scripted_cli(tmp_path: Path) -> CliHarness:
    succeeds, fails, missing, hangs = ["succeeds"], ["fails"], ["missing"], ["hangs"]
    answers: dict[tuple[str, ...], CliResult | None] = {("succeeds",): CliResult(0, "hello\n"), ("fails",): CliResult(3, "bad\n"), ("missing",): None, ("hangs",): None}
    return CliHarness(ScriptedKiroCli(answers), succeeds, fails, missing, hangs)


_FLAGS = "Usage: kiro-cli chat [OPTIONS]\n  --v3  --require-mcp-startup\n  --output-format <FORMAT>\n"
_READY = {
    ("kiro-cli", "--version"): CliResult(0, "kiro-cli 2.33.0\n"),
    ("kiro-cli", "chat", "--help"): CliResult(0, _FLAGS),
    ("kiro-cli", "whoami"): CliResult(0, "Logged in\n"),
}


def readiness_scripted(tmp_path: Path) -> ReadinessHarness:
    from ..access.testing import StaticAccess

    access = StaticAccess(tmp_path / "org")
    environment = DictEnvironment({"PATH": "/usr/bin"}, home=tmp_path / "user")

    def readiness(problem: str | None) -> RuntimeReadiness:
        state = MemoryKiroState()
        return KiroReadiness(
            OrgPaths(access.root), access.agents, access, FixedKiroPlaces(tmp_path / "state", problem), state, state,
            ScriptedKiroCli(_READY), environment,
        )

    return ReadinessHarness(readiness(None), readiness("the places are bad"), "kiro-cli")


def readiness_on_disk(tmp_path: Path) -> ReadinessHarness:
    """The real class over the files of an organization directory and shell scripts as kiro-cli."""
    access, files = charters_on_disk(tmp_path), fs_agents(tmp_path)
    kiro = _script(
        tmp_path.parent / f"{tmp_path.name}-kiro-cli",
        'case "$1" in\n  --version) echo "kiro-cli 2.33.0";;\n  chat) echo "--v3 --require-mcp-startup --output-format";;\n  whoami) echo ok;;\n  *) exit 9;;\nesac\n',
    )[0]
    home = tmp_path.parent / f"{tmp_path.name}-home"  # outside the organization, like the other harnesses

    def readiness(state_dir: str) -> RuntimeReadiness:
        environment = DictEnvironment({"PATH": "/usr/bin:/bin", "HIREARCHY_STATE_DIR": state_dir}, home=home)
        state = FsKiroState(system_clock(tmp_path))
        places = StateDirPlaces(OrgPaths(tmp_path), environment, "linux")
        return KiroReadiness(OrgPaths(tmp_path), files.directory, access.scopes, places, state, state, SubprocessKiroCli(), environment)

    good = str(tmp_path.parent / f"{tmp_path.name}-state")
    return ReadinessHarness(readiness(good), readiness("relative/state"), kiro)


def fixed_readiness(tmp_path: Path) -> ReadinessHarness:
    return ReadinessHarness(FixedReadiness(None), FixedReadiness("kiro-cli is not ready", "the kiro state is bad"), "kiro-cli")


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
    """The real access classes, places, directories and profile store over the files of an organization directory."""
    access, files = charters_on_disk(tmp_path), fs_agents(tmp_path)
    paths = OrgPaths(tmp_path)
    home = tmp_path.parent / f"{tmp_path.name}-home"  # outside the organization: the kiro state lies below it, and placement refuses one inside
    environment = DictEnvironment({"PATH": "/usr/bin", "KEEP": "me"}, home=home)
    places, state = StateDirPlaces(paths, environment, "linux"), fs_state(tmp_path)
    directory = places.home() / "agents"
    store = FsProfileStore(lambda: directory, fs_atomic_writer(tmp_path).writer)
    provisioner = OrgProfileProvisioner(paths, store, KiroConfinementPolicy(), StaticMcpServerLocator())
    builder = KiroRunCommandBuilder(
        "kiro-cli", LAUNCHER, paths, files.charters, access.scopes, access.models, provisioner, environment, places, state.dirs, state.audit
    )
    text = _disk_text(directory)

    def profile(name: str) -> JsonObject | None:
        raw = text(name)
        return None if raw is None else dict(json.loads(raw))

    return BuilderHarness(
        builder, tmp_path, environment, access.put_agent, access.put_config, provisioner, _disk_names(directory), profile, places, state, LAUNCHER
    )


def builder_in_memory(tmp_path: Path) -> BuilderHarness:
    from ..access.testing import StaticAccess

    access, store = StaticAccess(), MemoryProfileStore()
    paths, environment = OrgPaths(access.root), DictEnvironment({"PATH": "/usr/bin", "KEEP": "me"})
    places, state = FixedKiroPlaces(tmp_path / "state"), memory_state(tmp_path)
    provisioner = OrgProfileProvisioner(paths, store, KiroConfinementPolicy(), StaticMcpServerLocator())
    builder = KiroRunCommandBuilder(
        "kiro-cli", LAUNCHER, paths, access.agents, access, access, provisioner, environment, places, state.dirs, state.audit
    )

    def profile(name: str) -> JsonObject | None:
        raw = store.files.get(name)
        return None if raw is None else dict(json.loads(raw))

    return BuilderHarness(
        builder, access.root, environment, access.put_agent, access.put_config, provisioner,
        lambda: sorted(f"{name}.json" for name in store.files), profile, places, state, LAUNCHER,
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    ConfinementPolicy: [kiro_confinement],
    KiroPlaces: [state_dir_places, fixed_places],
    KiroStateDirs: [fs_state, memory_state],
    KiroHomeAudit: [fs_state, memory_state],
    KiroCli: [subprocess_cli, scripted_cli],
    RuntimeReadiness: [readiness_scripted, readiness_on_disk, fixed_readiness],
    ProfileStore: [fs_profile_store, memory_profile_store],
    McpServerLocator: [venv_locator, static_locator],
    ProfileProvisioner: [provisioner_on_disk, provisioner_in_memory],
    RunCommandBuilder: [builder_on_disk, builder_in_memory],
}
