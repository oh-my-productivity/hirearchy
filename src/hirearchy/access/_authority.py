"""``CharterAuthorityPolicy``: what a grantor may hand down, judged by its own charter."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast

from ..agents import CharterReader
from ..kernel import OrgError, OrgLayout, inside
from .api import AccessScopes, AuthorityPolicy


class CharterAuthorityPolicy(AuthorityPolicy):
    def __init__(self, paths: OrgLayout, charters: CharterReader, scopes: AccessScopes) -> None:
        self._paths = paths
        self._charters = charters
        self._scopes = scopes

    def check_authority(self, actor: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str] | None = None) -> None:
        meta, _ = self._charters.charter(actor)
        extra = set(tools) - set(cast("Iterable[str]", meta.get("tools") or []))
        if extra:
            raise OrgError(f"you cannot grant tools you do not have yourself: {', '.join(sorted(extra))}")
        if workspace:
            mine = cast("str | None", meta.get("workspace"))
            if not mine:
                raise OrgError("you have no workspace, so you cannot assign one")
            ws, base = Path(workspace).expanduser().resolve(), Path(mine).expanduser().resolve()
            if ws != base and base not in ws.parents:
                raise OrgError(f"a report's workspace must be inside yours ({mine})")
        if inputs:
            bases = [b for b in (self._scopes.workspace_of(actor), *self._scopes.inputs_of(actor)) if b is not None]
            if not bases:
                raise OrgError("you have no workspace or inputs, so you cannot assign inputs")
            for raw in inputs:
                if not any(inside(Path(raw).expanduser().resolve(), b) for b in bases):
                    raise OrgError(
                        f"a report's inputs must be inside your inputs or workspace ({', '.join(map(str, bases))}): {raw}"
                    )

    def check_inputs(self, inputs: object) -> list[str]:
        items = [inputs] if isinstance(inputs, str) else list(cast("Iterable[object]", inputs or []))
        out = []
        root = self._paths.root
        for raw in items:
            text = str(raw).strip()
            if not text:
                continue
            p = Path(text).expanduser()
            if not p.is_absolute():
                raise OrgError(f"an input must be an absolute path (got `{text}`)")
            p = p.resolve()
            if inside(p, root) or inside(root, p):
                raise OrgError(f"an input must not overlap the organization directory ({root}): {text}")
            out.append(text)
        return out
