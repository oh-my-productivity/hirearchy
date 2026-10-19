"""``FilesGuide``: the "Files" part of an agent's state (moved from ``Org._files_lines``)."""

from __future__ import annotations

from collections.abc import Mapping

from ..access import AccessScopes, ToolNaming
from ..kernel import OrgLayout
from ._ports import FilesLines


class FilesGuide(FilesLines):
    def __init__(self, scopes: AccessScopes, naming: ToolNaming, layout: OrgLayout) -> None:
        self._scopes = scopes
        self._naming = naming
        self._root = layout.root

    def lines(self, addr: str, meta: Mapping[str, object]) -> list[str]:
        raise NotImplementedError("red: C-prompts")
