"""``GuardedOrgFileWriter``: writes the files of an agent's own directory, and the charters of its direct reports."""

from __future__ import annotations

from pathlib import Path

from ..access import AccessScopes, AuthorityPolicy
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..kernel import OrgLayout
from ..settings import OrgSettings
from ._charter_merge import CharterMerge
from ._guard import WriteGuard
from .api import OrgFileStore, OrgFileWriter


class GuardedOrgFileWriter(OrgFileWriter):
    def __init__(
        self,
        layout: OrgLayout,
        store: OrgFileStore,
        guard: WriteGuard,
        merger: CharterMerge,
        agents: AgentDirectory,
        charters: CharterReader,
        registry: AgentRegistry,
        scopes: AccessScopes,
        authority: AuthorityPolicy,
        settings: OrgSettings,
    ) -> None:
        self._layout = layout
        self._store = store
        self._guard = guard
        self._merger = merger
        self._agents = agents
        self._charters = charters
        self._registry = registry
        self._scopes = scopes
        self._authority = authority
        self._settings = settings

    def resolve_write(self, actor: str, path: str) -> Path:
        raise NotImplementedError

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        raise NotImplementedError

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        raise NotImplementedError
