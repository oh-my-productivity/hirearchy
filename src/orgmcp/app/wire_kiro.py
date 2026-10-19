"""Providers of the ``kiro`` ports (ARCHITECTURE.md 6.1), and the constructors the legacy ``scheduler`` functions still need.

The module-level functions of ``scheduler.py`` (``kiro_profile_name``, ``ensure_kiro_profile``, ``file_confinement``, ``kiro_runner``,
``mcp_server_command``) have no runtime to take the ports from, and tests replace them one by one (``scheduler.mcp_server_command``,
``scheduler.ensure_kiro_profile``, ``scheduler.file_confinement``), so they ask this module for the real parts and hand it the functions
that are in force at the time of the call. They go away with ``scheduler.py`` (D-sched-1).
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import orgmcp

from ..access import AccessScopes, ModelResolver
from ..agents import CharterReader
from ..kernel import AtomicWriter, Environment, OrgLayout, OrgPaths, Provider
from ..kernel._system import FsAtomicWriter, OsEnvironment
from ..kiro import ConfinementPolicy, McpServerLocator, ProfileProvisioner, ProfileStore, RunCommandBuilder
from ..kiro._confinement import KiroConfinementPolicy
from ..kiro._mcp_locator import VenvMcpServerLocator
from ..kiro._profiles import FsProfileStore
from ..kiro._provisioner import OrgProfileProvisioner
from ..kiro._runner import KiroRunCommandBuilder
from ._builder import Builder
from .runtime import OrgRuntime

KIRO_BIN = "kiro-cli"  # the binary of the runtime's run command builder (``orgmcp run --kiro`` builds its own, from the legacy runner)


def package_dir() -> Path:
    """The directory of the ``orgmcp`` package (not the directory of the file that holds the code): the one entry of its ``__path__``, which
    is ``Path(orgmcp.__file__).parent`` for a regular package, and also exists for the bare package object that stands in for it when a module is
    imported first (``test_import_order``), where there is no ``__file__`` and no spec."""
    return Path(next(iter(orgmcp.__path__))).resolve()


def project_dir_of(package: Path) -> Path:
    """The checkout that ``uv --directory`` runs in when no console script is installed, for the ``orgmcp`` package directory ``package``:
    two levels above ``scheduler.py``, which is in that directory (``repo/src/orgmcp`` -> ``repo``; an installed wheel: ``site-packages/orgmcp`` ->
    the directory above ``site-packages``). Main computed it as ``Path(scheduler.__file__).resolve().parents[2]``."""
    return package.parents[1]


def project_dir() -> Path:
    """``project_dir_of`` the installed package."""
    return project_dir_of(package_dir())


def agents_dir(environment: Environment) -> Provider[Path]:
    """``~/.kiro/agents``, asked of the environment on every use (HOME may change between two calls)."""
    return lambda: environment.home() / ".kiro" / "agents"


def mcp_locator() -> McpServerLocator:
    """The locator of this process: the console script of the running interpreter, else ``uv`` in the checkout."""
    return VenvMcpServerLocator(lambda: Path(sys.executable), project_dir(), lambda name: shutil.which(name))


def confinement_policy() -> ConfinementPolicy:
    return KiroConfinementPolicy()


def register(b: Builder) -> None:
    b.provide(ConfinementPolicy, lambda b: KiroConfinementPolicy())
    b.provide(McpServerLocator, lambda b: mcp_locator())
    b.provide(ProfileStore, lambda b: FsProfileStore(agents_dir(b.get(Environment)), b.get(AtomicWriter)))
    b.provide(
        ProfileProvisioner,
        lambda b: OrgProfileProvisioner(b.get(OrgLayout), b.get(ProfileStore), b.get(ConfinementPolicy), b.get(McpServerLocator)),
    )
    b.provide(
        RunCommandBuilder,
        lambda b: KiroRunCommandBuilder(
            KIRO_BIN, b.get(OrgLayout), b.get(CharterReader), b.get(AccessScopes), b.get(ModelResolver), b.get(ProfileProvisioner),
            b.get(Environment),
        ),
    )


# ------------------------------------------------------------------------------ for the legacy scheduler functions (no runtime at hand)


class FunctionMcpServerLocator(McpServerLocator):
    """A locator that is a function: whatever ``scheduler.mcp_server_command`` is when the profile is written."""

    def __init__(self, command: Callable[[], dict[str, object]]) -> None:
        self._command = command

    def command(self) -> dict[str, object]:
        return self._command()


class FunctionConfinementPolicy(ConfinementPolicy):
    """A policy that is a function: whatever ``scheduler.file_confinement`` is when the profile is written."""

    def __init__(self, file_confinement: Callable[[Path, list[str], Path | None, list[Path]], tuple[list[str], dict[str, object]]]) -> None:
        self._file_confinement = file_confinement

    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        return self._file_confinement(org_root, list(tools), workspace, list(inputs))


class FunctionProfileProvisioner(ProfileProvisioner):
    """A provisioner that is two functions: whatever ``scheduler.ensure_kiro_profile`` and ``kiro_profile_name`` are when a run starts.

    A shared profile is asked for as ``ensure(tools)``, a confined one as ``ensure(tools, workspace=, inputs=, confine=True)``: the
    two call shapes of the old ``kiro_runner``, which tests replace by stubs of that signature."""

    def __init__(self, ensure: Callable[..., str], name: Callable[[Sequence[str]], str]) -> None:
        self._ensure = ensure
        self._name = name

    def profile_name(self, tools: Sequence[str]) -> str:
        return self._name(tools)

    def ensure_profile(
        self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None, confine: bool = False
    ) -> str:
        if confine:
            return self._ensure(tools, workspace=workspace, inputs=inputs, confine=True)
        return self._ensure(tools)


def profile_name(org_root: Path, tools: Sequence[str]) -> str:
    """The name of the profile of the organization at ``org_root`` for ``tools`` (nothing is read or written)."""
    return provisioner_at(org_root, Path("."), mcp_locator(), confinement_policy()).profile_name(tools)


def provisioner_at(root: Path, directory: Path, locator: McpServerLocator, confinement: ConfinementPolicy) -> ProfileProvisioner:
    """The provisioner of the organization at ``root`` that writes into ``directory``, with the system's atomic writer."""
    writer: AtomicWriter = FsAtomicWriter()
    return OrgProfileProvisioner(OrgPaths(root), FsProfileStore(lambda: directory, writer), confinement, locator)


def run_command_builder(runtime: OrgRuntime, kiro_bin: str, provisioner: ProfileProvisioner) -> RunCommandBuilder:
    """The run command builder over the ports of ``runtime`` and the given provisioner, with the environment of this process."""
    return KiroRunCommandBuilder(
        kiro_bin, runtime.paths, runtime.charters, runtime.access_scopes, runtime.model_resolver, provisioner, OsEnvironment()
    )
