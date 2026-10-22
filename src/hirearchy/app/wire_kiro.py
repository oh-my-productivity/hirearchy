"""Providers of the ``kiro`` ports (ARCHITECTURE.md 6.1), and the run command builder that ``hirearchy run --kiro BIN`` makes over a runtime."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from ..access import AccessScopes, ModelResolver
from ..agents import AgentDirectory, CharterReader
from ..kernel import AtomicWriter, Clock, Environment, OrgLayout, Provider
from ..kiro import (
    ConfinementPolicy, KiroCli, KiroHomeAudit, KiroPlaces, KiroStateDirs, McpServerLocator, ProfileProvisioner, ProfileStore, RunCommandBuilder,
    RuntimeReadiness,
)
from ..kiro._cli import SubprocessKiroCli
from ..kiro._confinement import KiroConfinementPolicy
from ..kiro._mcp_locator import VenvMcpServerLocator
from ..kiro._places import StateDirPlaces
from ..kiro._profiles import FsProfileStore
from ..kiro._provisioner import OrgProfileProvisioner
from ..kiro._readiness import KiroReadiness
from ..kiro._runner import KiroRunCommandBuilder
from ..kiro._state import FsKiroState
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


def launcher() -> tuple[str, ...]:
    """What comes before the kiro command of a run: the running interpreter, ``-I -S`` (no environment settings, no site-packages: the launcher
    imports only the standard library) and the launcher script, which sits in the ``kiro`` package (``test_kiro_packaged_paths`` pins it)."""
    return (sys.executable, "-I", "-S", str(package_dir() / "kiro" / "_launch.py"))


def kiro_agents_dir(places: KiroPlaces) -> Provider[Path]:
    """``agents/`` of the kiro home of the organization, asked of the places on every use (HOME and ``HIREARCHY_STATE_DIR`` may change between two calls)."""
    return lambda: places.home() / "agents"


def mcp_locator() -> McpServerLocator:
    """The locator of this process: the console script of the running interpreter, else ``uv`` in the checkout."""
    return VenvMcpServerLocator(lambda: Path(sys.executable), project_dir(), lambda name: shutil.which(name))


def confinement_policy() -> ConfinementPolicy:
    return KiroConfinementPolicy()


def register(b: Builder) -> None:
    b.provide(ConfinementPolicy, lambda b: KiroConfinementPolicy())
    b.provide(McpServerLocator, lambda b: mcp_locator())
    b.provide(KiroPlaces, lambda b: StateDirPlaces(b.get(OrgLayout), b.get(Environment), sys.platform))
    b.provide(KiroStateDirs, lambda b: FsKiroState(b.get(Clock)))
    b.provide(KiroHomeAudit, lambda b: FsKiroState(b.get(Clock)))
    b.provide(KiroCli, lambda b: SubprocessKiroCli())
    b.provide(
        RuntimeReadiness,
        lambda b: KiroReadiness(
            b.get(OrgLayout), b.get(AgentDirectory), b.get(AccessScopes), b.get(KiroPlaces), b.get(KiroStateDirs), b.get(KiroHomeAudit),
            b.get(KiroCli), b.get(Environment),
        ),
    )
    b.provide(ProfileStore, lambda b: FsProfileStore(kiro_agents_dir(b.get(KiroPlaces)), b.get(AtomicWriter)))
    b.provide(
        ProfileProvisioner,
        lambda b: OrgProfileProvisioner(b.get(OrgLayout), b.get(ProfileStore), b.get(ConfinementPolicy), b.get(McpServerLocator)),
    )
    b.provide(
        RunCommandBuilder,
        lambda b: KiroRunCommandBuilder(
            KIRO_BIN, launcher(), b.get(OrgLayout), b.get(CharterReader), b.get(AccessScopes), b.get(ModelResolver), b.get(ProfileProvisioner),
            b.get(Environment), b.get(KiroPlaces), b.get(KiroStateDirs), b.get(KiroHomeAudit),
        ),
    )


def run_command_builder(runtime: OrgRuntime, kiro_bin: str, provisioner: ProfileProvisioner) -> RunCommandBuilder:
    """The run command builder over the ports of ``runtime`` and the given provisioner. It reads the environment of the runtime (the one the places and
    the readiness check read too), so the runs and the credential check can never see different variables."""
    return KiroRunCommandBuilder(
        kiro_bin, launcher(), runtime.paths, runtime.charters, runtime.access_scopes, runtime.model_resolver, provisioner, runtime.environment,
        runtime.kiro_places, runtime.kiro_state_dirs, runtime.kiro_home_audit,
    )
