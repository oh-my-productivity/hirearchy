"""Creating a new organization (bootstrap).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .. import templates
from ..kernel import BOXES, join_frontmatter, OrgError
from ._compat import atomic_write
from ._facade_settings import DEFAULT_CONFIG

if TYPE_CHECKING:
    from .facade import Org


class BootstrapMixin:
    """Creating a new organization (bootstrap)."""

    @classmethod
    def init(cls, root: str | Path, mission: str | None = None, config: dict | None = None) -> Org:
        root = Path(root).expanduser().resolve()
        if (root / "ORG.md").exists():
            raise OrgError(f"already an organization: {root}")
        root.mkdir(parents=True, exist_ok=True)
        cfg = {**DEFAULT_CONFIG, **(config or {})}
        atomic_write(root / "ORG.md", join_frontmatter(cfg, templates.org_rules(mission)))
        for box in BOXES:
            (root / box).mkdir(exist_ok=True)
        (root / ".runtime").mkdir(exist_ok=True)
        (root / ".gitignore").write_text(".tmp-*\nruns/\n.kiro/\n.runtime/scheduler.pid\n.runtime/events/\n", encoding="utf-8")
        if shutil.which("git") and not (root / ".git").exists():
            subprocess.run(["git", "init", "-q"], cwd=root, check=False)
        org = cls(root)
        org.commit("init organization")
        return org
