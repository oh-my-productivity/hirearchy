"""``ValidatedPlanBasis``: the problems and the agents of a blueprint, for the organization it is planned against."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._protocols import AgentResolution, OrgContext, PlanBasis, WorkspaceRoots
from .api import Agent, BlueprintValidator, Issue


class ValidatedPlanBasis(PlanBasis):
    """The organization counts when it exists (it has a directory); before it does, the defaults apply and no name is taken."""

    def __init__(self, validator: BlueprintValidator, resolver: AgentResolution, roots: WorkspaceRoots, org: OrgContext) -> None:
        self._validator = validator
        self._resolver = resolver
        self._roots = roots
        self._org = org

    def issues(self, bp: Mapping[str, object], allowed_roots: Sequence[str | Path] | None, require_sources: bool = False) -> list[Issue]:
        return self._validator.validate(bp, org_exists=self._org.root() is not None, allowed_roots=allowed_roots, require_sources=require_sources)

    def agents(self, bp: Mapping[str, object], allowed_roots: Sequence[str | Path] | None) -> list[Agent]:
        return self._resolver.resolve(bp, self._org, self._roots.roots(allowed_roots), [])
