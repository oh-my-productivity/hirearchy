"""``ValidatedPlanBasis``: the problems and the agents of a blueprint, for the organization it is planned against."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._protocols import AgentResolution, OrgContext, PlanBasis, WorkspaceRoots
from .api import Agent, BlueprintValidator, Issue


class ValidatedPlanBasis(PlanBasis):
    def __init__(self, validator: BlueprintValidator, resolver: AgentResolution, roots: WorkspaceRoots, org: OrgContext) -> None:
        self._validator = validator
        self._resolver = resolver
        self._roots = roots
        self._org = org

    def issues(self, bp: Mapping[str, object], allowed_roots: Sequence[str | Path] | None) -> list[Issue]:
        raise NotImplementedError

    def agents(self, bp: Mapping[str, object], allowed_roots: Sequence[str | Path] | None) -> list[Agent]:
        raise NotImplementedError
