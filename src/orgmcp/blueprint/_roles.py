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
        raise NotImplementedError('red: C-blueprint-1')

    def get_role(self, name: str) -> Role | None:
        raise NotImplementedError('red: C-blueprint-1')
