"""The reads of the organization an extension's rules make (design 5.2): what an existing agent holds, and the deepest address there is."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from ..agents import AgentDirectory, CharterReader
from ..kernel import depth as org_depth
from ..services import ServiceCatalog
from ._protocols import AgentResolution, OrgContext, WorkspaceRoots
from ._shapes import Held
from .api import RoleLibrary, is_verifier


def as_int(value: object, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def held_by(addr: str, meta: Mapping[str, object], reports: int, roles: RoleLibrary) -> Held:
    """What the agent ``addr`` whose charter frontmatter is ``meta`` holds."""
    workspace = meta.get("workspace")
    return Held(
        addr, tuple(str(t) for t in cast("list[object]", meta.get("tools") or [])), str(workspace) if workspace else None,
        tuple(str(p) for p in cast("list[object]", meta.get("inputs") or [])), bool(meta.get("can_hire")), as_int(meta.get("max_children"), 5),
        reports, is_verifier(meta, roles),
    )


def deepest(agents: AgentDirectory) -> int:
    """The depth of the deepest agent there is (0 for an organization with none)."""
    return max((org_depth(a) for a in agents.agents()), default=0)


def read_held(agents: AgentDirectory, charters: CharterReader, roles: RoleLibrary, addr: str) -> Held:
    return held_by(addr, charters.charter(addr)[0], len(agents.children(addr)), roles)


@dataclass(frozen=True)
class Reads:
    """The ports an extension's rules read the organization through (design 5.2)."""

    org: OrgContext
    agents: AgentDirectory
    charters: CharterReader
    roles: RoleLibrary
    resolver: AgentResolution
    roots: WorkspaceRoots
    services: ServiceCatalog
