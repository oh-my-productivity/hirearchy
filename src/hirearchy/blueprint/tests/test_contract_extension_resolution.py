"""Contract of ``ExtensionResolution``: an extension blueprint read against the organization; it only reads, and says what is wrong in the issues of 5.2."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hirearchy.blueprint._protocols import ExtensionResolution
from hirearchy.blueprint.testing import IMPLEMENTATIONS, ExtensionHarness

from ._support import implementations, make

GOOD = {"reason": "r", "extend": {"limits": [{"agent": "lead", "max_children": 3}]}}


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ExtensionResolution]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ExtensionHarness:
    made = make(request, tmp_path, ExtensionHarness)
    assert isinstance(made.resolver, ExtensionResolution)
    return made


def test_an_extension_with_nothing_in_it_is_one_error_extend_form(h: ExtensionHarness) -> None:
    issues = h.resolver.resolve({"reason": "r", "extend": {}}).issues
    assert [(i.level, i.code) for i in issues] == [("error", "extend-form")]


def test_a_blueprint_that_is_not_an_extension_is_refused_as_extend_form(h: ExtensionHarness) -> None:
    issues = h.resolver.resolve({"mission": "m", "agents": [], "extend": {"limits": [{"agent": "lead", "max_children": 3}]}, "reason": "r"}).issues
    assert any(i.code == "extend-form" and i.path in ("mission", "agents") for i in issues)


def test_the_same_extension_gives_the_same_issues_and_the_blueprint_is_not_touched(h: ExtensionHarness) -> None:
    bp = copy.deepcopy({"reason": "r", "extend": {"add_robots": [1], "limits": [{"agent": "lead", "tools": ["write"]}]}})
    before = copy.deepcopy(bp)
    first, second = h.resolver.resolve(bp).issues, h.resolver.resolve(bp).issues
    assert first == second and bp == before and {i.code for i in first} == {"extend-form", "extend-keeps"}


def test_a_well_formed_form_has_no_form_issue(h: ExtensionHarness) -> None:
    assert not [i for i in h.resolver.resolve(GOOD).issues if i.code in ("extend-form", "extend-placeholder", "extend-keeps")]
