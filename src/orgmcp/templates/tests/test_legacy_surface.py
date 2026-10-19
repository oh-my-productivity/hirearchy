"""The names ``orgmcp.templates`` kept exporting when the module became a package (``LEGACY_EXPORTS``, until step E3).

Each old function is the new method under another name."""

from __future__ import annotations

import pytest

import orgmcp.templates as templates
from orgmcp.templates._documents import StaticDocumentTemplates
from orgmcp.templates._notices import StaticNotices

from ._cases import CASES, LEGACY_NAME, Case
from ._golden import expected, render

@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_an_old_function_returns_what_the_new_method_returns(case: Case) -> None:
    implementation = StaticDocumentTemplates() if case.port == "documents" else StaticNotices()
    legacy = getattr(templates, LEGACY_NAME[case.method])
    assert legacy(*case.args, **case.kwargs) == render(implementation, case)
    assert legacy(*case.args, **case.kwargs) == expected(case.name)


def test_the_constants_are_unchanged() -> None:
    assert templates.DEFAULT_MISSION == "(Describe the mission of this organization here.)"
    assert templates.ORG_RULES.format(mission="m") == expected("org_rules_mission").replace("Build the best research desk.", "m")
    assert list(templates.REVIEW_ACTIONS) == ["stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle"]
