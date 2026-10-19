"""``GuardedOrgFileReader``: reads files and directories where an agent may look."""

from __future__ import annotations

from pathlib import Path

from ..access import AccessScopes
from ..agents import AgentDirectory
from ..kernel import OrgLayout
from .api import OrgFileReader, OrgFileStore


class GuardedOrgFileReader(OrgFileReader):
    def __init__(self, layout: OrgLayout, store: OrgFileStore, agents: AgentDirectory, scopes: AccessScopes) -> None:
        self._layout = layout
        self._store = store
        self._agents = agents
        self._scopes = scopes

    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        raise NotImplementedError

    def read(self, path: str, actor: str | None = None) -> str:
        raise NotImplementedError
