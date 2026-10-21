"""``RootedPathChecker``: a user path is absolute, inside an allowed root, away from the organization and ``~/.kiro``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint._pathcheck import RootedPathChecker
from hirearchy.blueprint._protocols import PathChecking
from hirearchy.blueprint.api import Issue
from hirearchy.blueprint.testing import StaticOrgContext
from hirearchy.kernel.testing import DictEnvironment




class Case:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp.resolve()
        self.checker = RootedPathChecker(DictEnvironment(home=self.tmp / "home", cwd=self.tmp))
        self.issues: list[Issue] = []

    def check(self, raw: object, *, must_exist: bool = False, org: StaticOrgContext | None = None, roots: list[Path] | None = None) -> Path | None:
        return self.checker.check(raw, "where", self.issues, org or StaticOrgContext(), roots or [self.tmp], what="workspace", dir_must_exist=must_exist)

    def codes(self) -> list[tuple[str, str]]:
        return [(i.level, i.code) for i in self.issues]


@pytest.fixture
def case(tmp_path: Path) -> Case:
    return Case(tmp_path)


def test_a_path_inside_a_root_is_resolved(case: Case) -> None:
    assert case.check(str(case.tmp / "a" / ".." / "proj")) == case.tmp / "proj" and case.issues == []


def test_a_relative_path_is_refused_with_the_text_it_was_given(case: Case) -> None:
    assert case.check("rel/dir") is None
    assert case.issues == [Issue("error", "where", "workspace 'rel/dir' must be an absolute path; give the full path", "path")]


def test_a_root_itself_and_a_path_outside_every_root_are_refused(case: Case) -> None:
    assert case.check(str(case.tmp)) is None and case.check("/usr/local/x") is None and case.check("/") is None
    assert case.codes() == [("error", "path-root")] * 3
    assert f"outside the allowed roots ({case.tmp})" in case.issues[0].message and "or is a root itself" in case.issues[0].message


def test_the_kiro_configuration_of_the_home_directory_is_refused(case: Case) -> None:
    case.check(str(case.tmp / "home" / ".kiro" / "x"), roots=[case.tmp])
    assert case.issues == [Issue("error", "where", f"workspace {case.tmp / 'home' / '.kiro' / 'x'} is inside ~/.kiro (agent configuration); choose another directory", "path-root")]


def test_the_organization_directory_may_not_be_inside_the_path_nor_the_path_inside_it(case: Case) -> None:
    org = StaticOrgContext(root=case.tmp / "org")
    assert case.check(str(case.tmp / "org" / "inside"), org=org) is None and case.check(str(case.tmp / "org"), org=org) is None
    assert case.check(str(case.tmp), org=StaticOrgContext(root=case.tmp / "org"), roots=[case.tmp.parent]) is None
    assert [i.code for i in case.issues] == ["path-root"] * 3 and "overlaps the organization directory" in case.issues[0].message
    assert case.check(str(case.tmp / "other"), org=org) == case.tmp / "other"


def test_without_an_organization_nothing_overlaps(case: Case) -> None:
    assert case.check(str(case.tmp / "org" / "inside"), org=StaticOrgContext(root=None)) is not None and case.issues == []


def test_a_directory_that_must_exist(case: Case) -> None:
    (case.tmp / "there").mkdir()
    (case.tmp / "file").write_text("x", encoding="utf-8")
    assert case.check(str(case.tmp / "there"), must_exist=True) == case.tmp / "there" and case.issues == []
    assert case.check(str(case.tmp / "file"), must_exist=True) is None
    assert case.check(str(case.tmp / "new"), must_exist=True) == case.tmp / "new"
    assert case.check(str(case.tmp / "no" / "parent"), must_exist=True) is None
    assert case.codes() == [("error", "workspace"), ("warning", "workspace-new"), ("error", "workspace")]
    assert "exists but is not a directory" in case.issues[0].message and "apply will create it" in case.issues[1].message


def test_a_directory_that_need_not_exist(case: Case) -> None:
    assert case.check(str(case.tmp / "no" / "parent")) == case.tmp / "no" / "parent" and case.issues == []


def test_a_path_object_is_accepted(case: Case) -> None:
    assert case.check(case.tmp / "p") == case.tmp / "p"
