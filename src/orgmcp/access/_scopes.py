"""``CharterAccessScopes``: the workspace and inputs of an agent, read from its charter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..agents import AgentDirectory, CharterReader
from ..kernel import ROOT, norm
from ._rules import unconfined_read
from .api import AccessScopes


class CharterAccessScopes(AccessScopes):
    def __init__(self, agents: AgentDirectory, charters: CharterReader) -> None:
        self._agents = agents
        self._charters = charters

    def workspace_of(self, addr: str) -> Path | None:
        a = norm(addr)
        if a == ROOT or not self._agents.exists(a):
            return None
        raw = self._charters.charter(a)[0].get("workspace")
        return Path(str(raw)).expanduser().resolve() if raw else None

    def inputs_of(self, addr: str) -> list[Path]:
        a = norm(addr)
        if a == ROOT or not self._agents.exists(a):
            return []
        raw = self._charters.charter(a)[0].get("inputs")
        items = [raw] if isinstance(raw, str) else (raw if isinstance(raw, list) else [])
        return [Path(str(x)).expanduser().resolve() for x in items if str(x).strip()]

    def readable_roots(self, addr: str) -> list[Path]:
        a = norm(addr)
        roots = [*self.inputs_of(a)]
        roots += [w for s in self._agents.subtree(a) if (w := self.workspace_of(s)) is not None]
        return roots

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        return unconfined_read(meta)
