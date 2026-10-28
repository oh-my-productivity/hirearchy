"""Characterization of ``validate``: 166 mutated blueprints and what the validator of ``main`` answered for each (``golden/validate_corpus.json``).

The golden file was captured from the function of ``main`` before the validator moved; every issue is ``[level, path, message, code]`` with the
temporary directory written ``<TMP>``. The validator must answer the same issues in the same order, whatever role library it reads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hirearchy.blueprint import BlueprintValidator, Issue
from hirearchy.blueprint.testing import IMPLEMENTATIONS, StaticOrgContext, ValidatorHarness

from . import _corpus
from ._support import make


GOLDEN: dict[str, list[list[str]]] = json.loads(_corpus.GOLDEN.read_text(encoding="utf-8"))
NAMES = [name for name, _, _ in _corpus.MUTATIONS] + list(_corpus.ORG_SPECS)

# Every code of an Issue that ``validate`` can emit (``schema``: a blueprint that is not a mapping, in the contract suite).
ALL_CODES = {
    "agents", "authority", "budget", "budget-cap", "budget-low", "budget-tight", "children", "code-criteria", "code-needs", "code-tools",
    "criteria", "criterion-source", "criterion-words", "deliverable", "deliverable-format", "depth", "edits-others", "effort-floor", "exists", "inputs", "inputs-overlap", "kind", "limit-criterion",
    "manager-cheap-model", "mission", "model-floor", "model-policy", "model-review", "model-single", "name", "needs", "needs-approval", "needs-progress",
    "needs-scope", "path", "path-delivery", "path-parent", "path-root", "playbook", "read-nothing", "review", "scale", "service",
    "service-inputs", "service-name", "service-owner", "service-request", "shell-unconfined", "task", "template", "unknown-key",
    "vague-criterion", "verifier-cannot-read", "verifier-web", "web-current", "web-tools", "web-tools-partial", "workspace",
    "workspace-confinement", "workspace-new", "write-noncode",
}


@pytest.fixture(params=IMPLEMENTATIONS[BlueprintValidator], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ValidatorHarness:
    monkeypatch.setenv("HOME", str(tmp_path))  # ``~`` in a path is expanded by the standard library, from this variable
    return make(request, tmp_path, ValidatorHarness)


def shown(issues: list[Issue], tmp: Path, org_root: Path | None = None) -> list[list[str]]:
    return [[i.level, i.path, _corpus.shown(i.message, tmp, org_root), i.code] for i in issues]


@pytest.mark.parametrize("name", NAMES)
def test_the_validator_answers_what_the_function_of_main_answered(h: ValidatorHarness, name: str) -> None:
    if name in _corpus.ORG_SPECS:
        spec = _corpus.ORG_SPECS[name]
        root = h.tmp / "org"
        org = StaticOrgContext(root, spec.get("config"), spec.get("agents", ()), spec.get("services", ()))  # type: ignore[arg-type]
        bp = _corpus.org_cases(h.tmp, root)[name]
        issues = h.put_org(org).validate(bp, org_exists=True, allowed_roots=[h.tmp])
        assert shown(issues, h.tmp, root) == GOLDEN[name]
    else:
        bp = _corpus.cases(h.tmp)[name]
        assert shown(h.validator.validate(bp, allowed_roots=[h.tmp]), h.tmp) == GOLDEN[name]


