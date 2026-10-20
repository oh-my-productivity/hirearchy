"""Contract of ``PlanRenderer``: the plan the user approves. The text is golden: it is what the flat module wrote for every example blueprint."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.blueprint import Issue, PlanRenderer
from orgmcp.blueprint.testing import IMPLEMENTATIONS, RendererHarness, StaticOrgContext

from ._plans import KEYS, PROPOSED, base_dir, golden, load_text, scrub, template_at
from ._support import implementations, make


@pytest.fixture(params=implementations(IMPLEMENTATIONS[PlanRenderer]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RendererHarness:
    made = make(request, tmp_path, RendererHarness)
    assert isinstance(made.renderer, PlanRenderer)
    return made


def bp_of(key: str, base: Path) -> dict[str, object]:
    label, _, variant = key.partition("/")
    return load_text(template_at(label, variant, base))


@pytest.mark.parametrize("key", KEYS)
def test_the_details_are_the_text_the_flat_module_wrote(h: RendererHarness, key: str) -> None:
    base = base_dir(h.tmp)
    assert scrub(h.renderer.render_plan(bp_of(key, base), allowed_roots=[base]), base) == golden()["plans"][key]["details"]


@pytest.mark.parametrize("key", KEYS)
def test_the_block_for_the_user_is_the_text_the_flat_module_wrote(h: RendererHarness, key: str) -> None:
    base = base_dir(h.tmp)
    assert scrub(h.renderer.plan_for_user(bp_of(key, base), allowed_roots=[base]), base) == golden()["plans"][key]["block"]


@pytest.mark.parametrize("key", PROPOSED)
def test_propose_text_is_the_target_the_block_the_details_and_the_id(h: RendererHarness, key: str) -> None:
    base = base_dir(h.tmp)
    assert scrub(h.renderer.propose_text(bp_of(key, base), target="target line", allowed_roots=[base]), base) == golden()["plans"][key]["propose"]


@pytest.mark.parametrize("key", KEYS)
def test_the_block_says_draft_exactly_when_there_are_errors(h: RendererHarness, key: str) -> None:
    base = base_dir(h.tmp)
    first = h.renderer.plan_for_user(bp_of(key, base), allowed_roots=[base]).splitlines()[0]
    assert first.startswith("DRAFT - NOT READY") == bool(golden()["plans"][key]["errors"]) and (first == "PLAN FOR YOU" or first.startswith("DRAFT"))


def test_the_text_of_propose_org_when_the_blueprint_has_errors_has_no_id_and_no_show_line(h: RendererHarness) -> None:
    base = base_dir(h.tmp)
    text = h.renderer.propose_text(bp_of("analysis/raw", base), allowed_roots=[base])
    assert "plan_id: none (the blueprint has errors)" in text and "Show the block below" not in text and text.startswith("DRAFT - NOT READY")


def test_propose_text_without_a_target_starts_with_the_show_line(h: RendererHarness) -> None:
    base = base_dir(h.tmp)
    text = h.renderer.propose_text(bp_of("research/filled", base), allowed_roots=[base])
    assert text.startswith("Show the block below to the user exactly as written") and "\n\n--- machine marker: the user block ends above" in text


def test_propose_loads_what_it_is_given_and_writes_the_details(h: RendererHarness) -> None:
    base = base_dir(h.tmp)
    expected = golden()["plans"]["research/filled"]["details"]
    text = template_at("research", "filled", base)
    assert scrub(h.renderer.propose(text, allowed_roots=[base]), base) == expected
    assert scrub(h.renderer.propose(load_text(text), allowed_roots=[base]), base) == expected
    (base / "bp.yaml").write_text(text, encoding="utf-8")
    assert scrub(h.renderer.propose(base / "bp.yaml", allowed_roots=[base]), base) == expected
    assert scrub(h.renderer.propose(str(base / "bp.yaml"), allowed_roots=[base]), base) == expected


def test_the_issues_it_is_given_are_the_ones_it_shows(h: RendererHarness) -> None:
    base = base_dir(h.tmp)
    bp = bp_of("research/filled", base)
    given = [Issue("warning", "needs.scope", "say more", "x"), Issue("error", "mission", "no way", "y")]
    details = h.renderer.render_plan(bp, given, allowed_roots=[base])
    assert "Warnings (1):\n- needs.scope: say more" in details and "Errors (1) - must be fixed before this can be applied:\n- mission: no way" in details
    assert details.endswith("Cannot apply yet: tell me what to change.")
    block = h.renderer.plan_for_user(bp, given, allowed_roots=[base])
    assert block.startswith("DRAFT - NOT READY") and "Errors (1):\n- mission: no way" in block and block.endswith("Cannot apply yet.")
    assert "Warnings (1):\n- say more" in block
    clean = h.renderer.render_plan(bp, [], allowed_roots=[base])
    assert "Warnings" not in clean and "Errors" not in clean and clean.endswith("Reply 'approve' or tell me what to change.")


def test_the_organization_counts_when_it_exists(h: RendererHarness) -> None:
    base = base_dir(h.tmp)
    bp = bp_of("research/filled", base)
    over = h.put_org(StaticOrgContext(root=h.tmp / "org", agents=["lead"]))
    golden_org = golden()["with_org"]
    assert scrub(over.render_plan(bp, allowed_roots=[base]), base) == golden_org["details"]
    assert scrub(over.plan_for_user(bp, allowed_roots=[base]), base) == golden_org["block"]
    assert scrub(over.propose_text(bp, allowed_roots=[base]), base) == golden_org["propose"]
    assert "already exists" in golden_org["details"]


def test_the_plan_is_made_of_the_blueprint_only(h: RendererHarness) -> None:
    base = base_dir(h.tmp)
    bp = bp_of("documents-service/filled", base)
    before = repr(bp)
    first = h.renderer.render_plan(bp, allowed_roots=[base])
    assert repr(bp) == before and h.renderer.render_plan(bp, allowed_roots=[base]) == first


def test_the_block_is_compact(h: RendererHarness) -> None:
    base = base_dir(h.tmp)
    lines = h.renderer.plan_for_user(bp_of("research/filled", base), allowed_roots=[base]).splitlines()
    assert len(lines) <= 42
