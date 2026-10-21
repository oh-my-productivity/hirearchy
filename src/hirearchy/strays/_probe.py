"""The probe of a workspace for org files a built-in ``write`` left there (moved from ``scheduler._stray_probe`` and ``_strays_since``)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import cast

from ..access import AccessScopes
from ..agents import CharterReader
from ._ports import MtimeReader
from .api import StrayProbe


class WorkspaceStrayProbe(StrayProbe):
    """Where an agent's built-in ``write`` leaves org files in its workspace, and what is there now.

    kiro's ``write`` starts in the workspace, so ``write("lead/analyst/MEMORY.md")`` lands in ``<workspace>/lead/analyst/``.
    Probed: ``<workspace>/<address>`` (a directory) and ``<workspace>/<address>/MEMORY.md``, each with its mtime.
    """

    def __init__(self, scopes: AccessScopes, charters: CharterReader, mtimes: MtimeReader) -> None:
        self._scopes = scopes
        self._charters = charters
        self._mtimes = mtimes

    def probe(self, addr: str) -> dict[str, float]:
        meta, _ = self._charters.charter(addr)
        ws = self._scopes.workspace_of(addr)
        if "write" not in cast("Iterable[str]", meta.get("tools") or []) or ws is None:
            return {}
        tree = ws.joinpath(*addr.split("/"))
        out: dict[str, float] = {}
        for path in (tree, tree / "MEMORY.md"):
            mtime = self._mtimes.mtime(path)
            if mtime is not None:
                out[str(path)] = mtime
        return out

    def found_since(self, before: Mapping[str, float], after: Mapping[str, float]) -> list[str]:
        new = [p for p, mtime in after.items() if p not in before or (p.endswith("MEMORY.md") and mtime > before[p])]
        return [p for p in new if not (p.endswith("/MEMORY.md") and p.rsplit("/", 1)[0] in new)]  # the tree says it all
