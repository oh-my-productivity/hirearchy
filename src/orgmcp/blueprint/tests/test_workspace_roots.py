"""``EnvironmentWorkspaceRoots``: where workspaces and the deliverable path may be."""

from __future__ import annotations

import os
from pathlib import Path

from orgmcp.blueprint._protocols import WorkspaceRoots
from orgmcp.blueprint._roots import EnvironmentWorkspaceRoots
from orgmcp.kernel.testing import DictEnvironment




def roots(tmp: Path, variables: dict[str, str] | None = None) -> EnvironmentWorkspaceRoots:
    (tmp / "home").mkdir(exist_ok=True)
    (tmp / "work").mkdir(exist_ok=True)
    (tmp / "temp").mkdir(exist_ok=True)
    return EnvironmentWorkspaceRoots(DictEnvironment(variables, cwd=tmp / "work", home=tmp / "home"), lambda: tmp / "temp")


def test_the_given_roots_are_used_resolved_and_with_the_home_expanded(tmp_path: Path, monkeypatch: object) -> None:
    given: list[str | Path] = [tmp_path / "a" / ".." / "b", "~/x"]
    out = roots(tmp_path).roots(given)
    assert out[0] == (tmp_path / "b").resolve() and out[1] == Path("~/x").expanduser().resolve()


def test_without_given_roots_the_variable_lists_them(tmp_path: Path) -> None:
    listed = os.pathsep.join([str(tmp_path / "p"), "", str(tmp_path / "q")])
    assert roots(tmp_path, {"ORGMCP_WORKSPACE_ROOTS": listed}).roots() == [(tmp_path / "p").resolve(), (tmp_path / "q").resolve()]
    assert roots(tmp_path, {"ORGMCP_WORKSPACE_ROOTS": listed}).roots([]) == [(tmp_path / "p").resolve(), (tmp_path / "q").resolve()]


def test_given_roots_win_over_the_variable(tmp_path: Path) -> None:
    assert roots(tmp_path, {"ORGMCP_WORKSPACE_ROOTS": str(tmp_path / "p")}).roots([tmp_path / "g"]) == [(tmp_path / "g").resolve()]


def test_the_default_is_home_the_temp_directory_slash_tmp_and_the_working_directory_without_duplicates(tmp_path: Path) -> None:
    out = roots(tmp_path).roots()
    assert out == [(tmp_path / "home").resolve(), (tmp_path / "temp").resolve(), Path("/tmp").resolve(), (tmp_path / "work").resolve()]
    same = EnvironmentWorkspaceRoots(DictEnvironment(cwd=tmp_path, home=tmp_path), lambda: tmp_path)
    assert same.roots() == [tmp_path.resolve(), Path("/tmp").resolve()]


def test_an_empty_variable_is_no_variable(tmp_path: Path) -> None:
    assert roots(tmp_path, {"ORGMCP_WORKSPACE_ROOTS": ""}).roots()[0] == (tmp_path / "home").resolve()
