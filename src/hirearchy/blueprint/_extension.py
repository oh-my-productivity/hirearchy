"""``ExtensionResolver``: an extension blueprint read against the organization it extends (design 5.2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._extension_form import form_issues
from ._protocols import ExtensionResolution, OrgContext
from ._shapes import Extension


class ExtensionResolver(ExtensionResolution):
    def __init__(self, org: OrgContext) -> None:
        self._org = org

    def resolve(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False) -> Extension:
        return Extension(form_issues(bp))
