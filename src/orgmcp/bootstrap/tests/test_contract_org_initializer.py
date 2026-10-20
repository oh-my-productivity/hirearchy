"""Contract of ``OrgInitializer``: the real one over the real ports, the real one over the in-memory ports, and the in-memory one;
and all of them when the git program does not exist. The expected bytes were captured from ``Org.init`` of ``main``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.bootstrap import INITIAL_IGNORE_LINES, OrgInitializer
from orgmcp.bootstrap.testing import IMPLEMENTATIONS, WITHOUT_GIT, InitHarness
from orgmcp.kernel import OrgError

from ._cases import CASES, DIRECTORIES, Case, expected



def build(request: pytest.FixtureRequest, tmp_path: Path) -> InitHarness:
    made = cast(Callable[[Path], InitHarness], request.param)(tmp_path)
    assert isinstance(made.initializer, OrgInitializer)
    return made


@pytest.fixture(params=IMPLEMENTATIONS[OrgInitializer], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> InitHarness:
    return build(request, tmp_path)


@pytest.fixture(params=WITHOUT_GIT, ids=lambda factory: factory.__name__)
def no_git(request: pytest.FixtureRequest, tmp_path: Path) -> InitHarness:
    return build(request, tmp_path)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_org_md_is_the_settings_over_the_defaults_and_the_rules(h: InitHarness, case: Case) -> None:
    h.initializer.init(h.root, case.mission, case.config)
    assert h.org_md() == expected(f"org_md_{case.name}.md")


def test_the_root_gets_its_four_boxes_and_the_runtime_directory(h: InitHarness) -> None:
    h.initializer.init(h.root)
    assert h.directories() == DIRECTORIES


def test_gitignore_starts_with_the_initial_lines(h: InitHarness) -> None:
    h.initializer.init(h.root)
    assert h.gitignore() == expected("gitignore.txt") == "".join(f"{line}\n" for line in INITIAL_IGNORE_LINES)


def test_the_first_commit_is_init_organization(h: InitHarness) -> None:
    h.initializer.init(h.root)
    assert h.has_repository() is True
    assert h.commits() == ["init organization"]


def test_an_existing_org_md_is_refused_and_nothing_is_changed(h: InitHarness) -> None:
    h.put_org_md("mine\n")
    with pytest.raises(OrgError) as refused:
        h.initializer.init(h.root, "m")
    assert str(refused.value) == f"already an organization: {h.root}"
    assert h.org_md() == "mine\n"
    assert (h.directories(), h.gitignore(), h.commits(), h.has_repository()) == ([], None, [], False)


def test_a_second_init_is_refused(h: InitHarness) -> None:
    h.initializer.init(h.root, "FIRST-MISSION")
    with pytest.raises(OrgError, match="already an organization"):
        h.initializer.init(h.root, "SECOND-MISSION")
    text = h.org_md() or ""
    assert "FIRST-MISSION" in text and "SECOND-MISSION" not in text
    assert h.commits() == ["init organization"]


def test_without_git_everything_but_the_repository_is_made(no_git: InitHarness) -> None:
    no_git.initializer.init(no_git.root, None)
    assert no_git.org_md() == expected("org_md_no_mission.md")
    assert no_git.directories() == DIRECTORIES
    assert no_git.gitignore() == expected("gitignore.txt")
    assert (no_git.has_repository(), no_git.commits()) == (False, [])
