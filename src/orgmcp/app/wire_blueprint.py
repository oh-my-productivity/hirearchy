"""Providers of the ``blueprint`` ports (ARCHITECTURE.md 6.1), and the parts the legacy module-level functions of ``blueprint`` work with.

The role templates stay in ``orgmcp/roles`` (package data, risk 8 of the architecture): the directory is found here, from the location of this
module, and handed to ``PackagedRoleLibrary``; the classes of ``blueprint`` never look at their own file name.

The legacy functions (``validate``, ``get_role``, ...) take an optional ``Org`` and read the process they run in; they cannot take their parts from
a runtime, so ``legacy_parts`` makes them once and ``fields_blueprint`` installs them when the application package is loaded. They go away with
the last legacy caller (E3)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..blueprint._assembly import LegacyParts
from ..kiro import ConfinementPolicy
from ._builder import Builder


def package_dir() -> Path:
    raise NotImplementedError("red: C-blueprint-1")


def roles_dir_of(package: Path) -> Path:
    raise NotImplementedError("red: C-blueprint-1")


def roles_dir() -> Path:
    raise NotImplementedError("red: C-blueprint-1")


class PatchPointConfinementPolicy(ConfinementPolicy):
    """A policy that is a function: whatever ``scheduler.file_confinement`` is when the plan asks what the built-in ``read`` may open."""

    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        raise NotImplementedError("red: C-blueprint-1")


def legacy_parts() -> LegacyParts:
    raise NotImplementedError("red: C-blueprint-1")


def register(b: Builder) -> None:
    """Red: nothing is provided yet."""
