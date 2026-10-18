"""The names ``orgmcp.templates`` kept exporting when the module became a package (``LEGACY_EXPORTS``, until step E3).

Each old function is the new method under another name; ``kiro_profile`` stays here until step B-kiro moves it."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import cast

import pytest

import orgmcp.templates as templates
from orgmcp.kernel import JsonObject
from orgmcp.templates._documents import StaticDocumentTemplates
from orgmcp.templates._notices import StaticNotices

from ._cases import CASES, KIRO_PROFILE_ARGS, LEGACY_NAME, Case
from ._golden import expected, render

@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_an_old_function_returns_what_the_new_method_returns(case: Case) -> None:
    implementation = StaticDocumentTemplates() if case.port == "documents" else StaticNotices()
    legacy = getattr(templates, LEGACY_NAME[case.method])
    assert legacy(*case.args, **case.kwargs) == render(implementation, case)
    assert legacy(*case.args, **case.kwargs) == expected(case.name)


@pytest.mark.parametrize("name", sorted(KIRO_PROFILE_ARGS))
def test_the_kiro_profile_is_unchanged(name: str) -> None:
    args, kwargs = KIRO_PROFILE_ARGS[name]
    kiro_profile = cast(Callable[..., JsonObject], templates.kiro_profile)  # the cases pass keyword arguments from a table
    profile = kiro_profile(*args, **kwargs)
    assert json.dumps(profile, indent=2) + "\n" == expected(name, ".json")


def test_the_constants_are_unchanged() -> None:
    assert templates.DEFAULT_MISSION == "(Describe the mission of this organization here.)"
    assert templates.ORG_RULES.format(mission="m") == expected("org_rules_mission").replace("Build the best research desk.", "m")
    assert list(templates.REVIEW_ACTIONS) == ["stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle"]
