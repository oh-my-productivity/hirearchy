"""What is left of the legacy surface of the scheduler: ``file_confinement``, which the legacy blueprint functions still ask through
``app.wire_blueprint`` (the module of another step of E3 that deletes them). It goes with them (E3-close).

The composition root's module is looked up late: an entry point may not import ``orgmcp.app`` (the layers contract)."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import cast


def file_confinement(
    org_root: Path, tools: list[str], workspace: Path | None, inputs: list[Path]
) -> tuple[list[str], dict[str, object]]:
    """(allowedTools, toolsSettings) that confine kiro's built-in ``read``/``write`` by path (see ``KiroConfinementPolicy``)."""
    policy = importlib.import_module("orgmcp.app.wire_kiro").confinement_policy()
    return cast("tuple[list[str], dict[str, object]]", policy.file_confinement(org_root, tools, workspace, inputs))
