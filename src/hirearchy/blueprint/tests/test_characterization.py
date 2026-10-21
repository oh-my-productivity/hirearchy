"""What the skeletons already satisfy, and must keep satisfying: these tests cannot fail for want of an implementation, so they are not red.

* the classes subclass the interface they implement (a skeleton does that too);
* the constants of the model and of the plan block keep the values the flat module had;
* the golden file of ``validate`` names every rule (the data, not the validator);
* ``kernel.inside`` answers like the function it replaced (``blueprint._within``, a duplicate that is deleted by this step).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import hirearchy.blueprint as bpm
from hirearchy.blueprint import api
from hirearchy.blueprint._access import PolicyAccessReport
from hirearchy.blueprint._budgeting import KINDS, REWORK_RUNS, SLACK, TIGHT, BudgetPlanner
from hirearchy.blueprint._files import FsTextFiles
from hirearchy.blueprint._loader import PATH_NAME_MAX, YamlBlueprintLoader
from hirearchy.blueprint._org import NoOrgContext, PresentOrAbsentOrg, RuntimeOrgContext
from hirearchy.blueprint._pathcheck import RootedPathChecker
from hirearchy.blueprint._protocols import (
    AccessReport,
    AgentResolution,
    BudgetPlanning,
    OrgContext,
    OrgContexts,
    PathChecking,
    ServiceRules,
    TextFiles,
    WorkspaceRoots,
)
from hirearchy.blueprint._resolver import AgentResolver
from hirearchy.blueprint._roles import PackagedRoleLibrary
from hirearchy.blueprint._roots import EnvironmentWorkspaceRoots
from hirearchy.blueprint._service_rules import ServiceBlueprintRules
from hirearchy.blueprint._text import CLIP, GOAL_CLIP
from hirearchy.blueprint._validator import RuleBlueprintValidator
from hirearchy.blueprint.testing import (
    MemoryRoleLibrary,
    MemoryTextFiles,
    ScriptedConfinementPolicy,
    StaticOrgContext,
)
from hirearchy.kernel import inside

from . import _corpus

IMPLEMENTS: list[tuple[type, type]] = [
    (PackagedRoleLibrary, api.RoleLibrary), (MemoryRoleLibrary, api.RoleLibrary),
    (YamlBlueprintLoader, api.BlueprintLoader), (RuleBlueprintValidator, api.BlueprintValidator),
    (FsTextFiles, TextFiles), (MemoryTextFiles, TextFiles),
    (NoOrgContext, OrgContext), (RuntimeOrgContext, OrgContext), (StaticOrgContext, OrgContext),
    (PresentOrAbsentOrg, OrgContexts), (RootedPathChecker, PathChecking), (EnvironmentWorkspaceRoots, WorkspaceRoots),
    (AgentResolver, AgentResolution), (BudgetPlanner, BudgetPlanning), (PolicyAccessReport, AccessReport),
    (ServiceBlueprintRules, ServiceRules), (api.Issue, api.IssueText),
]


@pytest.mark.parametrize("cls, protocol", IMPLEMENTS, ids=lambda x: x.__name__)
def test_a_class_subclasses_the_interface_it_implements(cls: type, protocol: type) -> None:
    assert issubclass(cls, protocol)


def test_the_scripted_confinement_policy_is_a_confinement_policy() -> None:
    from hirearchy.kiro import ConfinementPolicy

    assert isinstance(ScriptedConfinementPolicy(), ConfinementPolicy)


def test_the_constants_of_the_model_are_the_ones_of_the_flat_module() -> None:
    assert (SLACK, TIGHT, KINDS) == (1.25, 1.10, ("manager", "author", "verifier"))
    assert REWORK_RUNS == {"manager": 2, "author": 1, "verifier": 1}


def test_the_limits_of_the_plan_block_and_of_a_file_name() -> None:
    assert (CLIP, GOAL_CLIP, PATH_NAME_MAX) == (400, 800, 1024)


def test_the_corpus_makes_every_rule_fire() -> None:
    from .test_validate_corpus import ALL_CODES, GOLDEN, NAMES

    emitted = {row[3] for rows in GOLDEN.values() for row in rows}
    assert emitted == ALL_CODES
    assert set(GOLDEN) == set(NAMES)


def test_the_golden_file_is_sorted_json_of_issues() -> None:
    golden = json.loads(_corpus.GOLDEN.read_text(encoding="utf-8"))
    assert all(len(row) == 4 and row[0] in ("error", "warning") for rows in golden.values() for row in rows)


def test_the_removed_duplicate_of_inside_answered_the_same(tmp_path: Path) -> None:
    """``blueprint._within`` was ``p == base or base in p.parents``: ``kernel.inside`` replaced it."""
    def within(p: Path, base: Path) -> bool:
        return p == base or base in p.parents

    paths = [tmp_path, tmp_path / "a", tmp_path / "a" / "b", tmp_path / "ab", tmp_path.parent, Path("/"), Path("/tmp")]
    for p in paths:
        for base in paths:
            assert inside(p, base) == within(p, base)


def test_the_names_that_moved_to_the_api_are_the_api_objects() -> None:
    assert (bpm.Issue, bpm.Agent, bpm.Role, bpm.BlueprintError, bpm.errors) == (api.Issue, api.Agent, api.Role, api.BlueprintError, api.errors)

