"""Contract of ``BlueprintValidator``: every problem of a blueprint, errors that block and warnings that are shown; the organization only counts when it exists."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hirearchy.blueprint import BlueprintValidator, Issue, errors
from hirearchy.blueprint.testing import IMPLEMENTATIONS, StaticOrgContext, ValidatorHarness

from . import _corpus
from ._support import implementations, make


@pytest.fixture(params=implementations(IMPLEMENTATIONS[BlueprintValidator]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ValidatorHarness:
    made = make(request, tmp_path, ValidatorHarness)
    assert isinstance(made.validator, BlueprintValidator)
    return made


def codes(issues: list[Issue], level: str | None = None) -> set[str]:
    return {i.code for i in issues if level is None or i.level == level}


def test_the_shipped_example_has_no_error_and_one_warning(h: ValidatorHarness) -> None:
    issues = h.validator.validate(_corpus.research(h.tmp), allowed_roots=[h.tmp])
    assert not errors(issues)
    assert codes(issues) - {"criterion-source", "criterion-words"} == {"path-delivery"}


def test_what_is_not_a_mapping_is_a_schema_error(h: ValidatorHarness) -> None:
    assert h.validator.validate([], allowed_roots=[h.tmp]) == [  # type: ignore[arg-type]
        Issue("error", "", "a blueprint is a mapping with mission, needs, agents and task", "schema")]


def test_an_empty_blueprint_lacks_everything(h: ValidatorHarness) -> None:
    issues = h.validator.validate({}, allowed_roots=[h.tmp])
    assert {"mission", "needs", "task", "agents"} <= codes(issues, "error")


def test_the_blueprint_is_not_changed_and_the_answer_is_the_same_twice(h: ValidatorHarness) -> None:
    bp = _corpus.services_only(h.tmp)
    before = copy.deepcopy(bp)
    first = h.validator.validate(bp, allowed_roots=[h.tmp])
    assert bp == before and h.validator.validate(bp, allowed_roots=[h.tmp]) == first


def test_the_issues_say_where_and_how(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    bp["agents"] = [{"name": "lead", "template": "wizard"}]
    issue = next(i for i in h.validator.validate(bp, allowed_roots=[h.tmp]) if i.code == "template")
    assert issue.level == "error" and issue.path == "agents[lead]"
    assert issue.message.startswith("unknown template 'wizard'; available: ") and "researcher" in issue.message
    assert issue.render() == f"error: agents[lead]: {issue.message}"


def test_a_path_outside_the_allowed_roots_is_refused(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)
    bp["needs"]["deliverable"]["path"] = "/usr/local/report.md"  # type: ignore[index]
    assert "path-root" in codes(h.validator.validate(bp, allowed_roots=[h.tmp]), "error")
    other = h.tmp / "elsewhere"
    other.mkdir()
    bp["needs"]["deliverable"]["path"] = str(other / "report.md")  # type: ignore[index]
    assert "path-root" in codes(h.validator.validate(bp, allowed_roots=[h.tmp / "deliverables"]), "error")
    assert "path-root" not in codes(h.validator.validate(bp, allowed_roots=[h.tmp]), "error")


def test_the_default_roots_are_the_home_the_temp_directory_and_the_working_directory(h: ValidatorHarness) -> None:
    bp = _corpus.research(h.tmp)  # its deliverable is in tmp, which is the working directory of the process
    assert "path-root" not in codes(h.validator.validate(bp), "error")
    bp["needs"]["deliverable"]["path"] = "/usr/local/report.md"  # type: ignore[index]
    assert "path-root" in codes(h.validator.validate(bp), "error")


def test_without_an_organization_nothing_is_taken_and_the_defaults_apply(h: ValidatorHarness) -> None:
    taken = h.put_org(StaticOrgContext(agents=["lead"], services=["weekly-brief"], config={"max_depth": 1}))
    bp = _corpus.services_only(h.tmp)
    assert not errors(h.validator.validate(bp, allowed_roots=[h.tmp]))
    assert not errors(taken.validate(bp, allowed_roots=[h.tmp]))  # the validator over an organization, asked as if there were none


def test_an_agent_that_exists_in_the_organization_is_an_error(h: ValidatorHarness) -> None:
    validator = h.put_org(StaticOrgContext(agents=["lead"]))
    issues = validator.validate(_corpus.research(h.tmp), org_exists=True, allowed_roots=[h.tmp])
    exists = [i for i in issues if i.code == "exists"]
    assert [i.path for i in exists] == ["agents[lead]"] and "already exists in this organization" in exists[0].message


def test_a_service_name_taken_in_the_organization_is_an_error(h: ValidatorHarness) -> None:
    validator = h.put_org(StaticOrgContext(agents=["other"], services=["weekly-brief"]))
    issues = validator.validate(_corpus.services_only(h.tmp), org_exists=True, allowed_roots=[h.tmp])
    assert any(i.code == "service-name" and "already exists in this organization" in i.message for i in issues)


def test_the_limits_of_the_organization_apply(h: ValidatorHarness) -> None:
    validator = h.put_org(StaticOrgContext(config={"max_depth": 1}))
    issues = validator.validate(_corpus.code(h.tmp), org_exists=True, allowed_roots=[h.tmp])
    depth = [i for i in issues if i.code == "depth"]
    assert depth and "exceeds the organization's max_depth 1" in depth[0].message
    assert "depth" not in codes(h.validator.validate(_corpus.code(h.tmp), allowed_roots=[h.tmp]))


def test_a_workspace_may_not_overlap_the_organization_directory(h: ValidatorHarness) -> None:
    root = h.tmp / "org"
    validator = h.put_org(StaticOrgContext(root=root))
    bp = _corpus.code(h.tmp)
    bp["needs"]["workspace"] = str(root / "inside")  # type: ignore[index]
    issues = validator.validate(bp, org_exists=True, allowed_roots=[h.tmp])
    assert any(i.code == "path-root" and f"overlaps the organization directory {root}" in i.message for i in issues)
    assert not any("overlaps the organization" in i.message for i in validator.validate(bp, allowed_roots=[h.tmp]))


def test_the_playbook_cap_is_the_organizations(h: ValidatorHarness) -> None:
    bp = _corpus.services_only(h.tmp)
    bp["services"][0]["playbook"] = "one two three four five six"  # type: ignore[index]
    assert "playbook" not in codes(h.validator.validate(bp, allowed_roots=[h.tmp]))
    validator = h.put_org(StaticOrgContext(config={"playbook_max_words": 5}))
    found = [i for i in validator.validate(bp, org_exists=True, allowed_roots=[h.tmp]) if i.code == "playbook"]
    assert found and "the playbook is 6 words; the limit is 5" in found[0].message
