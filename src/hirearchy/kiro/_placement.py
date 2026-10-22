"""``placement_problem``: no place an agent may read can touch hirearchy's kiro state (docs/design/kiro-runtime-v3.md 8.3)."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))  # follows links (reads them, writes nothing): the comparison is between real locations


def placement_problem(roots: Sequence[Path], readable: Sequence[tuple[Path, str]]) -> str | None:
    """The first reason a readable place and a root (``<state>/kiro-home``, ``<state>/kiro-cwd``) collide, else ``None``.

    ``readable`` holds ``(path, what it is)`` pairs, e.g. ``(ws, "workspace of ceo/eng")``. The roots hold the homes and scratch
    trees of every organization of this user, so a place inside one is refused whoever owns the part it lies in."""
    real_roots = [_real(root) for root in roots]
    for base, what in readable:
        real_base = _real(base)
        for real_root in real_roots:
            if real_base == real_root or real_root in real_base.parents:
                return (
                    f"the {what} {real_base} is inside hirearchy's kiro state {real_root}, which holds the kiro homes and working "
                    "directories of every organization: move it out of there"
                )
            if real_base in real_root.parents:
                return (
                    f"hirearchy's kiro state {real_root} is inside the {what} {real_base}: that agent could read the transcripts "
                    "kiro keeps there; set HIREARCHY_STATE_DIR to a folder outside every workspace, input and the organization"
                )
    return None
