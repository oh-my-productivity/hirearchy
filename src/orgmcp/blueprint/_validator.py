"""``RuleBlueprintValidator``: what went wrong in the usability studies, as checks over a blueprint.

Errors block ``apply``; warnings are shown in the plan."""
from __future__ import annotations
import math
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast
from ..kernel import JsonObject, inside
from ..settings import config_default_model
from ._budgeting import TIGHT
from ._protocols import AccessReport, AgentResolution, BudgetPlanning, OrgContexts, PathChecking, ServiceRules, WorkspaceRoots
from ._resolver import declared_inputs, review_roots
from ._rules import NO_WEB, TIERED, WEB_STRONG, WEB_WEAK, blob, delivers_directly, edits_others_files, has_ws_tools, is_code, review_required, vague
from ._shapes import Estimate
from ._view import NEEDS_KEYS, REQUEST_KEYS, TASK_KEYS, WEB_TOOLS, WRITE_TOOLS, criteria_of, deliverable_of, is_plain, mapping_or_empty, s, services_of, svc_criteria, unknown
from .api import BlueprintValidator, Issue

class RuleBlueprintValidator(BlueprintValidator):

    def __init__(self, resolver: AgentResolution, paths: PathChecking, budgets: BudgetPlanning, access: AccessReport, services: ServiceRules, roots: WorkspaceRoots, orgs: OrgContexts) -> None:
        self._resolver = resolver
        self._paths = paths
        self._budgets = budgets
        self._access = access
        self._services = services
        self._roots = roots
        self._orgs = orgs

    def validate(self, bp: Mapping[str, object], *, org_exists: bool=False, allowed_roots: Sequence[str | Path] | None=None) -> list[Issue]:
        raise NotImplementedError('red: C-blueprint-1')
