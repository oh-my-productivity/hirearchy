"""The reads of the organization an extension's rules make (design 5.2): what an existing agent holds, and the deepest address there is."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import cast

from ..agents import AgentDirectory, CharterReader
from ..kernel import depth as org_depth
from ..services import ServiceCatalog, ServiceEvidence
from ._protocols import AgentResolution, BudgetPlanning, ContinuedCriteria, OrgContext, RootTasks, ServiceRules, WorkspaceRoots
from ._shapes import Held
from .api import Issue
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
    evidence: ServiceEvidence
    budgets: BudgetPlanning
    rules: ServiceRules
    tasks: RootTasks
    continued: ContinuedCriteria


_SERVICE_PATH = re.compile(r"^services\[([^\]]*)\](.*)$")


def retargeted(found: Sequence[Issue], where: Mapping[str, str]) -> list[Issue]:
    """The issues of a blueprint's ``services`` rules (paths ``services[<name>]...``) as issues of the extension entries they came from (``where``:
    service name -> the entry's path); an issue with another path is kept as it is."""
    out: list[Issue] = []
    for i in found:
        m = _SERVICE_PATH.match(i.path)
        out.append(replace(i, path=where[m.group(1)] + m.group(2)) if m and m.group(1) in where else i)
    return out
