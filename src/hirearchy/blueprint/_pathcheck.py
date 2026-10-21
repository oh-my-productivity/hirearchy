"""``RootedPathChecker``: a user path must be absolute, inside an allowed root, and away from the organization and ``~/.kiro``."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from ..kernel import Environment, inside
from ._protocols import OrgContext, PathChecking
from ._view import s
from .api import Issue


class RootedPathChecker(PathChecking):
    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def check(
        self, raw: object, where: str, issues: list[Issue], org: OrgContext, roots: Sequence[Path], *, what: str, dir_must_exist: bool,
    ) -> Path | None:
        text = s(raw)
        p = Path(os.path.expanduser(text))
        if not p.is_absolute():
            issues.append(Issue("error", where, f"{what} '{text}' must be an absolute path; give the full path", "path"))
            return None
        p = p.resolve()
        if p.parent == p or not any(inside(p, r) and p != r for r in roots):
            shown = ", ".join(str(r) for r in roots)
            issues.append(Issue("error", where, f"{what} {p} is outside the allowed roots ({shown}) or is a root itself; choose a project directory inside one (extend with --allow-root or $HIREARCHY_WORKSPACE_ROOTS)", "path-root"))
            return None
        if inside(p, (self._environment.home() / ".kiro").resolve()):
            issues.append(Issue("error", where, f"{what} {p} is inside ~/.kiro (agent configuration); choose another directory", "path-root"))
            return None
        org_root = org.root()
        if org_root is not None and (inside(p, org_root) or inside(org_root, p)):
            issues.append(Issue("error", where, f"{what} {p} overlaps the organization directory {org_root}; agents must work in a separate directory", "path-root"))
            return None
        if dir_must_exist:
            if p.exists() and not p.is_dir():
                issues.append(Issue("error", where, f"{what} {p} exists but is not a directory", "workspace"))
                return None
            if not p.exists():
                if p.parent.is_dir():
                    issues.append(Issue("warning", where, f"{p} does not exist yet; apply will create it", "workspace-new"))
                else:
                    issues.append(Issue("error", where, f"{p} does not exist and neither does its parent; create it or fix the path", "workspace"))
                    return None
        return p
