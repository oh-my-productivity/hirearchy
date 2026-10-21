"""An in-memory ``access`` and the registry the contract suites iterate over.

``StaticAccess`` answers all four ports for charters kept in memory. It passes the same contract suites as the real classes over the
files of an organization (``tests/test_contract_*.py``), so a consumer's unit test may use it instead of directories on disk.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents.testing import MemoryAgents, fs_agents
from ..kernel import JsonObject, OrgPaths, join_frontmatter
from ..settings.testing import MemoryOrgSettings, fs_org_settings
from ._authority import CharterAuthorityPolicy
from ._models import CharterModelResolver
from ._naming import CharterToolNaming
from ._scopes import CharterAccessScopes
from .api import AccessScopes, AuthorityPolicy, ModelResolver, ToolNaming

DEFAULT_ORG_MD = "---\nmax_depth: 4\n---\n# Organization\n"
CHARTER_BODY = "# Role\n\nDo the work."


class StaticAccess(AccessScopes, AuthorityPolicy, ToolNaming, ModelResolver):
    """The four ports over agents and an ORG.md kept in memory: ``put_agent`` makes an agent, ``put_config`` replaces ORG.md."""

    def __init__(self, root: Path | None = None, org_md: str = DEFAULT_ORG_MD, agents: MemoryAgents | None = None) -> None:
        """``agents``: the agent files this access reads, when a consumer's world keeps them for other ports too (default: its own)."""
        self.agents = agents if agents is not None else MemoryAgents()
        if root is not None:
            self.agents.root = root
        self.settings = MemoryOrgSettings(org_md)
        self.root = self.agents.root
        self._scopes = CharterAccessScopes(self.agents, self.agents)
        self._authority = CharterAuthorityPolicy(OrgPaths(self.root), self.agents, self._scopes)
        self._naming = CharterToolNaming(self.agents)
        self._models = CharterModelResolver(self.agents, self.settings)

    def put_agent(self, addr: str, meta: Mapping[str, object]) -> None:
        """``addr`` becomes an agent whose charter has this frontmatter."""
        self.agents.put(f"{addr}/AGENT.md", join_frontmatter(dict(meta), CHARTER_BODY))

    def put_config(self, org_md: str) -> None:
        """ORG.md becomes this text."""
        self.settings.write_raw(org_md)

    def workspace_of(self, addr: str) -> Path | None:
        return self._scopes.workspace_of(addr)

    def inputs_of(self, addr: str) -> list[Path]:
        return self._scopes.inputs_of(addr)

    def readable_roots(self, addr: str) -> list[Path]:
        return self._scopes.readable_roots(addr)

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        return self._scopes.unconfined_read(meta)

    def check_authority(self, actor: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str] | None = None) -> None:
        self._authority.check_authority(actor, tools, workspace, inputs)

    def check_inputs(self, inputs: object) -> list[str]:
        return self._authority.check_inputs(inputs)

    def tool_names(self, addr: str) -> dict[str, str]:
        return self._naming.tool_names(addr)

    def default_model(self) -> str:
        return self._models.default_model()

    def model_for(self, addr: str) -> str:
        return self._models.model_for(addr)


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class AccessHarness:
    """The four ports over one organization, and the means to prepare its files behind their back."""

    scopes: AccessScopes
    authority: AuthorityPolicy
    naming: ToolNaming
    models: ModelResolver
    root: Path  # the organization directory as the ports see it
    put_agent: Callable[[str, JsonObject], None]  # ``addr`` becomes an agent whose charter has this frontmatter
    put_config: Callable[[str], None]  # ORG.md becomes this text


def charters_on_disk(tmp_path: Path) -> AccessHarness:
    """The real classes over the files of an organization directory."""
    paths, files, document = OrgPaths(tmp_path), fs_agents(tmp_path), fs_org_settings(tmp_path)
    scopes = CharterAccessScopes(files.directory, files.charters)

    def put_agent(addr: str, meta: JsonObject) -> None:
        files.put(f"{addr}/AGENT.md", join_frontmatter(meta, CHARTER_BODY))

    document.put(DEFAULT_ORG_MD)
    return AccessHarness(
        scopes,
        CharterAuthorityPolicy(paths, files.charters, scopes),
        CharterToolNaming(files.charters),
        CharterModelResolver(files.charters, document.settings),
        tmp_path,
        put_agent,
        document.put,
    )


def static_access(tmp_path: Path) -> AccessHarness:
    """The in-memory fake."""
    fake = StaticAccess()
    return AccessHarness(fake, fake, fake, fake, fake.root, fake.put_agent, fake.put_config)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    AccessScopes: [charters_on_disk, static_access],
    AuthorityPolicy: [charters_on_disk, static_access],
    ToolNaming: [charters_on_disk, static_access],
    ModelResolver: [charters_on_disk, static_access],
}
