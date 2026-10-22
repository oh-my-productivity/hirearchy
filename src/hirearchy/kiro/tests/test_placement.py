"""``placement_problem``: no readable place of an agent may touch hirearchy's kiro state (docs/design/kiro-runtime-v3.md 8.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kiro._placement import placement_problem


@pytest.fixture
def roots(tmp_path: Path) -> tuple[Path, Path]:
    state = tmp_path / "state"
    return state / "kiro-home", state / "kiro-cwd"


def inside_message(what: str, base: Path, root: Path) -> str:
    return (
        f"the {what} {base} is inside hirearchy's kiro state {root}, which holds the kiro homes and working directories of every "
        "organization: move it out of there"
    )


def contains_message(what: str, base: Path, root: Path) -> str:
    return (
        f"hirearchy's kiro state {root} is inside the {what} {base}: that agent could read the transcripts kiro keeps there; "
        "set HIREARCHY_STATE_DIR to a folder outside every workspace, input and the organization"
    )


def test_unrelated_places_are_fine(tmp_path: Path, roots: tuple[Path, Path]) -> None:
    readable = [(tmp_path / "org", "organization"), (tmp_path / "ws", "workspace of dev"), (tmp_path / "in", "input of dev")]
    assert placement_problem(roots, readable) is None
    assert placement_problem(roots, []) is None


def test_a_sibling_with_the_same_prefix_is_unrelated(tmp_path: Path, roots: tuple[Path, Path]) -> None:
    assert placement_problem(roots, [(roots[0].parent / "kiro-home-2", "workspace of dev")]) is None


def test_a_place_equal_to_a_root_is_refused(roots: tuple[Path, Path]) -> None:
    assert placement_problem(roots, [(roots[1], "workspace of ceo/eng")]) == inside_message("workspace of ceo/eng", roots[1], roots[1])


def test_a_place_inside_a_root_is_refused(roots: tuple[Path, Path]) -> None:
    base = roots[0] / "org-1" / "agents"
    assert placement_problem(roots, [(base, "input of dev")]) == inside_message("input of dev", base, roots[0])


def test_a_place_that_contains_a_root_is_refused(tmp_path: Path, roots: tuple[Path, Path]) -> None:
    assert placement_problem(roots, [(tmp_path, "organization")]) == contains_message("organization", tmp_path, roots[0])


def test_a_place_that_contains_the_state_itself_is_refused(roots: tuple[Path, Path]) -> None:
    state = roots[0].parent
    assert placement_problem(roots, [(state, "workspace of dev")]) == contains_message("workspace of dev", state, roots[0])


@pytest.mark.parametrize("what", ["organization", "workspace of ceo/eng", "input of ceo/eng"])
def test_each_kind_of_readable_place_is_named(roots: tuple[Path, Path], what: str) -> None:
    problem = placement_problem(roots, [(roots[0] / "x", what)])
    assert problem is not None and f"the {what} " in problem and "\n" not in problem


def test_an_input_inside_another_organizations_home_is_refused(roots: tuple[Path, Path]) -> None:
    base = roots[0] / "other-org-0123456789abcdef" / "sessions"
    assert placement_problem(roots, [(base, "input of dev")]) == inside_message("input of dev", base, roots[0])


def test_a_workspace_inside_another_organizations_scratch_root_is_refused(roots: tuple[Path, Path]) -> None:
    base = roots[1] / "other-org-0123456789abcdef" / "agent-12345678"
    assert placement_problem(roots, [(base, "workspace of dev")]) == inside_message("workspace of dev", base, roots[1])


def test_a_place_is_compared_through_symlinks(tmp_path: Path, roots: tuple[Path, Path]) -> None:
    roots[0].mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(roots[0], target_is_directory=True)
    problem = placement_problem(roots, [(link / "org-1", "workspace of dev")])
    assert problem is not None and "is inside hirearchy's kiro state" in problem


def test_the_first_problem_is_reported(roots: tuple[Path, Path], tmp_path: Path) -> None:
    problem = placement_problem(roots, [(tmp_path / "fine", "organization"), (roots[1] / "a", "input of x"), (roots[0] / "b", "input of y")])
    assert problem is not None and "input of x" in problem
