"""The model floor in ``validate`` and ``apply`` (docs/design/org-agent-model-floor.md 3): a plan whose models are outside the allowed set, or
whose organization sets an effort below ``high``, has errors, so ``apply`` refuses it and creates nobody. Runs over every validator."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.blueprint import BlueprintValidator, Issue
from hirearchy.blueprint.testing import IMPLEMENTATIONS, StaticOrgContext, ValidatorHarness

from . import _corpus
from ._support import implementations, make

PAIR = "claude-sonnet-5.5, claude-opus-5.5"
OUT = ["claude-haiku-4.5", "claude-sonnet-4.6"]
Bp = dict[str, object]


def m1(model: str, allowed: str = PAIR) -> str:
    return f'model "{model}" is not allowed for org agents; allowed: {allowed} (only the user can widen this set)'


@pytest.fixture(params=implementations(IMPLEMENTATIONS[BlueprintValidator]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ValidatorHarness:
    return make(request, tmp_path, ValidatorHarness)


def needs(bp: Bp) -> Bp:
    return cast(Bp, bp["needs"])


def kids(bp: Bp) -> list[Bp]:
    return cast("list[Bp]", cast("list[Bp]", bp["agents"])[0]["children"])


def floor_issues(h: ValidatorHarness, bp: Bp, config: dict[str, object] | None = None) -> list[Issue]:
    """The ``model-floor`` and ``effort-floor`` issues of ``bp`` in an organization with this settings block."""
    org = StaticOrgContext(h.tmp / "org", config)
    issues = h.put_org(org).validate(bp, org_exists=True, allowed_roots=[h.tmp])
    return [i for i in issues if i.code in ("model-floor", "effort-floor")]


@pytest.mark.parametrize("tier", ["cheap", "strong"])
@pytest.mark.parametrize("model", OUT)
def test_tier_ids_outside_the_set_are_errors(h: ValidatorHarness, tier: str, model: str) -> None:
    bp = _corpus.research(h.tmp)
    needs(bp)["models"] = {"cheap": "claude-sonnet-5.5", "strong": "claude-opus-5.5", tier: model}
    assert floor_issues(h, bp) == [Issue("error", f"needs.models.{tier}", m1(model), "model-floor")]


def test_an_explicit_agent_model_outside_the_set_is_an_error(h: ValidatorHarness) -> None:
    for model in OUT:
        bp = _corpus.research(h.tmp)
        kids(bp)[1]["model"] = model  # the writer
        assert floor_issues(h, bp) == [Issue("error", "agents[lead/writer]", m1(model), "model-floor")]


def test_the_floor_models_are_admitted(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    needs(bp)["models"] = {"cheap": "claude-sonnet-5.5", "strong": "claude-opus-5.5"}
    needs(bp)["model_policy"] = "cheap drafting, strong review"
    kids(bp)[1]["model"] = "claude-opus-5.5"
    kids(bp)[0]["model"] = "claude-sonnet-5.5"
    assert floor_issues(h, bp) == []


def test_the_tier_names_are_not_model_ids(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    kids(bp)[1]["model"] = "cheap"
    kids(bp)[2]["model"] = "strong"
    assert floor_issues(h, bp) == []


def test_an_org_default_outside_the_set_is_an_error_when_an_agent_would_run_on_it(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    needs(bp).pop("models")  # every tier is the org's default
    assert floor_issues(h, bp, {"default_model": "claude-haiku-4.5"}) == [
        Issue("error", "ORG.md default_model", m1("claude-haiku-4.5"), "model-floor")
    ]
    # every agent names an allowed id: nobody would run on the default
    named = _corpus.research(h.tmp)
    needs(named).pop("models")
    lead = cast("list[Bp]", named["agents"])[0]
    lead["model"] = "claude-opus-5.5"
    for kid in kids(named):
        kid["model"] = "claude-sonnet-5.5"
    assert floor_issues(h, named, {"default_model": "claude-haiku-4.5"}) == []


def test_a_default_that_a_tier_already_names_is_reported_once(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    needs(bp)["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-opus-5.5"}
    got = floor_issues(h, bp, {"default_model": "claude-haiku-4.5"})
    assert [(i.path, i.message) for i in got] == [("needs.models.cheap", m1("claude-haiku-4.5"))]


def test_an_org_default_inside_the_set_is_fine(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    needs(bp).pop("models")
    assert floor_issues(h, bp, {"default_model": "claude-opus-5.5"}) == []


def test_an_org_effort_below_the_floor_is_an_error(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    assert floor_issues(h, bp, {"effort": "medium"}) == [
        Issue("error", "ORG.md effort", 'effort "medium" is not allowed for org agents; allowed: high, xhigh, max', "effort-floor")
    ]
    assert floor_issues(h, bp, {"effort": "xhigh"}) == []


def test_a_widened_set_admits_its_extra_ids(h: ValidatorHarness) -> None:
    config: dict[str, object] = {"extra_allowed_models": ["claude-haiku-4.5", "claude-sonnet-4.6"]}
    bp = _corpus.research(h.tmp)
    needs(bp)["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-sonnet-4.6"}
    kids(bp)[1]["model"] = "claude-haiku-4.5"
    assert floor_issues(h, bp, config) == []
    kids(bp)[1]["model"] = "claude-3-opus"
    assert floor_issues(h, bp, config) == [
        Issue("error", "agents[lead/writer]", m1("claude-3-opus", PAIR + ", claude-haiku-4.5, claude-sonnet-4.6"), "model-floor")
    ]


def test_a_plan_without_an_organization_is_checked_against_the_default_set(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    needs(bp)["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-opus-5.5"}
    got = [i for i in h.validator.validate(bp, allowed_roots=[h.tmp]) if i.code == "model-floor"]
    assert got == [Issue("error", "needs.models.cheap", m1("claude-haiku-4.5"), "model-floor")]
