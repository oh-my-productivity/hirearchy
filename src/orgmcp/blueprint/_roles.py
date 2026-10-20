"""``PackagedRoleLibrary``: the role templates that ship with orgmcp (``roles/*.md``: a frontmatter and the charter text)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import cast

from ..kernel import NAME_RE, split_frontmatter
from .api import Role, RoleLibrary


class PackagedRoleLibrary(RoleLibrary):
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def role_names(self) -> list[str]:
        return sorted(p.stem for p in self._directory.glob("*.md"))

    def get_role(self, name: str) -> Role | None:
        p = self._directory / f"{name}.md"
        if not NAME_RE.fullmatch(name) or not p.is_file():
            return None
        meta, body = split_frontmatter(p.read_text(encoding="utf-8"))
        return Role(
            name, str(meta["title"]), str(meta["kind"]), str(meta.get("tier", "cheap")), tuple(cast("Iterable[str]", meta.get("tools") or ())),
            int(cast("int | str", meta.get("base_runs", 2))), str(meta.get("summary", "")), body.strip(),
        )
