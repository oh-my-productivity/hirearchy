"""``AgentResolver``: the agents of a blueprint, flattened parents first and settled (tools, workspace, inputs, authority, model).

Also the readings of the ``inputs`` a blueprint names, which the resolver and the validator share."""
from __future__ import annotations
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from ..kernel import NAME_RE, RESERVED, JsonObject, inside
from ..settings import config_default_model
from ._protocols import AgentResolution, OrgContext, PathChecking
from ._view import AGENT_KEYS, WRITE_TOOLS, items, mapping_or_empty, needs_of, s, unknown
from .api import Agent, Issue, RoleLibrary

def input_entries(value: object, where: str, issues: list[Issue]) -> list[tuple[str, bool]]:
    """``inputs`` as (path, overlap_ok) pairs. An entry is a path or ``{path: ..., allow_overlap: true}``."""
    raise NotImplementedError('red: C-blueprint-1')

def declared_inputs(bp: Mapping[str, object]) -> list[tuple[str, str, bool]]:
    """(where, path, overlap_ok) for every input the blueprint names: ``needs.inputs`` and each agent's ``inputs``."""
    raise NotImplementedError('red: C-blueprint-1')

def review_roots(agents: Sequence[Agent], project_ws: Path | None) -> list[Path]:
    """The folders the work under review lives in: the project workspace and every author's workspace."""
    raise NotImplementedError('red: C-blueprint-1')

def _verifier_inputs(agents: Sequence[Agent], by: Mapping[str, Agent], project_ws: Path | None) -> None:
    """A verifier reads what it reviews: the project workspace and the authors' workspaces become read-only ``inputs``
    wherever it has no write access to them (orgmcp ``read`` accepts paths inside a caller's inputs; kiro ``read`` too
    when it holds that tool). An explicit ``inputs`` list is the blueprint's decision; ``validate`` warns when it falls
    short. Managers hold the union of their reports' inputs, so authority keeps narrowing."""
    raise NotImplementedError('red: C-blueprint-1')

class AgentResolver(AgentResolution):

    def __init__(self, roles: RoleLibrary, paths: PathChecking) -> None:
        self._roles = roles
        self._paths = paths

    def _walk(self, raw_agents: object, parent: Agent | None, out: list[Agent], issues: list[Issue], where: str) -> list[str]:
        """Flatten the nested agents list into ``out`` (parents first); returns the addresses created at this level."""
        raise NotImplementedError('red: C-blueprint-1')

    def resolve(self, bp: Mapping[str, object], org: OrgContext, roots: Sequence[Path], issues: list[Issue]) -> list[Agent]:
        raise NotImplementedError('red: C-blueprint-1')
