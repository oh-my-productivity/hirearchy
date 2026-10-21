"""Providers of the ``kiro`` ports (ARCHITECTURE.md 6.1), and the run command builder that ``hirearchy run --kiro BIN`` makes over a runtime."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from ..access import AccessScopes, ModelResolver
from ..agents import CharterReader
from ..kernel import AtomicWriter, Environment, OrgLayout, Provider
from ..kernel._system import OsEnvironment
from ..kiro import ConfinementPolicy, McpServerLocator, ProfileProvisioner, ProfileStore, RunCommandBuilder
from ..kiro._confinement import KiroConfinementPolicy
from ..kiro._mcp_locator import VenvMcpServerLocator
from ..kiro._profiles import FsProfileStore
from ..kiro._provisioner import OrgProfileProvisioner
from ..kiro._runner import KiroRunCommandBuilder
from ._builder import Builder
from .runtime import OrgRuntime

KIRO_BIN = "kiro-cli"  # the binary of the runtime's run command builder (``hirearchy run --kiro BIN`` builds its own, with ``run_command_builder``)


def package_dir() -> Path:
    """The directory of the ``hirearchy`` package, from the location of this module (``hirearchy/app/wire_kiro.py``: two levels up).

    It is not read from the ``hirearchy`` package object (``import hirearchy`` runs the package ``__init__``, which imports the CLI and so
    every entry point). This module
    sits in a fixed place of the package in a checkout and in a wheel alike, and ``test_kiro_packaged_paths`` pins the result to
    ``Path(hirearchy.__file__).parent`` so that moving this file cannot go unnoticed."""
    return Path(__file__).resolve().parent.parent


def project_dir_of(package: Path) -> Path:
    """The checkout that ``uv --directory`` runs in when no console script is installed, for the ``hirearchy`` package directory ``package``:
    two levels above ``scheduler.py``, which is in that directory (``repo/src/hirearchy`` -> ``repo``; an installed wheel: ``site-packages/hirearchy`` ->
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


def run_command_builder(runtime: OrgRuntime, kiro_bin: str, provisioner: ProfileProvisioner) -> RunCommandBuilder:
    """The run command builder over the ports of ``runtime`` and the given provisioner, with the environment of this process."""
    return KiroRunCommandBuilder(
        kiro_bin, runtime.paths, runtime.charters, runtime.access_scopes, runtime.model_resolver, provisioner, OsEnvironment()
    )
