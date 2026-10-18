"""``CharterAccessScopes``: the workspace and inputs of an agent, read from its charter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..agents import AgentDirectory, CharterReader
from .api import AccessScopes


class CharterAccessScopes(AccessScopes):
    def __init__(self, agents: AgentDirectory, charters: CharterReader) -> None:
        self._agents = agents
        self._charters = charters

    def workspace_of(self, addr: str) -> Path | None:
        raise NotImplementedError

    def inputs_of(self, addr: str) -> list[Path]:
        raise NotImplementedError

    def readable_roots(self, addr: str) -> list[Path]:
        raise NotImplementedError

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        raise NotImplementedError
