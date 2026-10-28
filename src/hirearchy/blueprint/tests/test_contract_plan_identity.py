"""Contract of ``PlanIdentity``: which blueprint a plan was made for. The id is a pure function of the normalized blueprint (one implementation, no fake)."""

from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
import yaml

from hirearchy.blueprint import PlanIdentity
from hirearchy.blueprint._identity import HashPlanIdentity

from . import _corpus
from ._plans import LABELS, fill, golden, load_text


@pytest.fixture
def identity() -> PlanIdentity:
    made = HashPlanIdentity()
    assert isinstance(made, PlanIdentity)
    return made


@pytest.mark.parametrize("label", LABELS)
def test_the_id_of_every_example_is_the_one_the_flat_module_made(identity: PlanIdentity, label: str) -> None:
    bp = load_text(fill(golden()["examples"][label]))
    assert identity.plan_id(bp) == golden()["plan_ids"][label]


def test_the_id_is_twelve_hex_digits(identity: PlanIdentity) -> None:
    assert re.fullmatch(r"[0-9a-f]{12}", identity.plan_id({"mission": "m"}))


def test_the_same_blueprint_in_another_layout_has_the_same_id(identity: PlanIdentity) -> None:
    bp = {"mission": "m", "needs": {"scope": "s", "kind": "research"}, "agents": [{"name": "lead", "template": "manager"}]}
    text = yaml.safe_dump(bp, sort_keys=False)
    reordered = {"agents": bp["agents"], "needs": {"kind": "research", "scope": "s"}, "mission": "m"}
    commented = "# a comment\n" + text.replace("mission: m", "mission:   m   # inline")
    assert identity.plan_id(bp) == identity.plan_id(reordered) == identity.plan_id(load_text(commented)) == identity.plan_id(load_text(text))


def test_lenient_acceptance_text_and_the_list_it_means_are_the_same_blueprint(identity: PlanIdentity) -> None:
    as_text = {"mission": "m", "task": {"acceptance": "- one\n- two"}}
    as_list = {"mission": "m", "task": {"acceptance": ["one", "two"]}}
    assert identity.plan_id(as_text) == identity.plan_id(as_list)


def test_any_change_to_a_value_changes_the_id(identity: PlanIdentity, tmp_path: Path) -> None:
    bp = _corpus.services_only(tmp_path)
    changed = copy.deepcopy(bp)
    changed["services"][0]["budget"] = 23  # type: ignore[index]
    assert identity.plan_id(bp) != identity.plan_id(changed)


def test_the_organization_does_not_matter(identity: PlanIdentity) -> None:
    # nothing but the blueprint goes in: the same value twice, with no organization to give
    bp = {"mission": "m", "agents": [{"name": "lead"}]}
    assert identity.plan_id(bp) == identity.plan_id(copy.deepcopy(bp))


def test_what_is_not_a_mapping_is_refused_like_the_loader_does(identity: PlanIdentity) -> None:
    from hirearchy.blueprint import BlueprintError

    with pytest.raises(BlueprintError, match="a blueprint is a mapping"):
        identity.plan_id([])  # type: ignore[arg-type]


def test_an_extensions_plan_id_is_12_hex_over_the_blueprint_and_the_fingerprint() -> None:
    from hirearchy.blueprint.testing import ScriptedFingerprint

    ext = {"reason": "r", "extend": {"limits": [{"agent": "lead", "max_children": 3}]}}
    org, other = ScriptedFingerprint("org one"), ScriptedFingerprint("org two")
    first, second = HashPlanIdentity(org).plan_id(ext), HashPlanIdentity(other).plan_id(ext)
    assert re.fullmatch(r"[0-9a-f]{12}", first) and first != second  # the organization is part of the id
    assert HashPlanIdentity(org).plan_id(ext) == first and len(org.asked) == 2
    changed = {**ext, "reason": "another"}
    assert HashPlanIdentity(org).plan_id(changed) != first  # so is the blueprint
    assert HashPlanIdentity().plan_id(ext) == HashPlanIdentity().plan_id(copy.deepcopy(ext))  # without a fingerprint: the blueprint alone
    full = {"mission": "m", "agents": [{"name": "lead"}]}
    assert HashPlanIdentity(org).plan_id(full) == HashPlanIdentity().plan_id(full) and len(org.asked) == 3  # a full blueprint never asks for it
