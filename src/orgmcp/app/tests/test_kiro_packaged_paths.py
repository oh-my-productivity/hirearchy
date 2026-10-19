"""Risk 8 of ARCHITECTURE.md (path arithmetic that depends on file depth): the checkout of the uv fallback of the MCP command.

On ``main`` it is ``Path(scheduler.__file__).resolve().parents[2]``. The code that builds the command moved one directory deeper
(``orgmcp/kiro/_mcp_locator.py``), so the directory is computed in the wiring from the ``orgmcp`` package, and these tests prove that the
values are the same, in a checkout and in an installed wheel (whose layout is rebuilt here; a real wheel was built with ``uv build`` and
inspected by hand, see the report of the step)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

import orgmcp
import orgmcp.scheduler as scheduler
from orgmcp.app import wire_kiro

REPO = Path(__file__).resolve().parents[4]


def main_project_dir(package: Path) -> Path:
    """The expression of ``main`` (scheduler.py: ``PROJECT_DIR = Path(__file__).resolve().parents[2]``), for a package directory."""
    return (package / "scheduler.py").resolve().parents[2]


def test_the_package_directory_is_the_one_of_the_orgmcp_module() -> None:
    assert wire_kiro.package_dir() == Path(orgmcp.__file__).resolve().parent == Path(scheduler.__file__).resolve().parent.parent  # the package directory of orgmcp.scheduler


def test_the_project_directory_of_the_checkout_is_the_value_of_main() -> None:
    assert wire_kiro.project_dir() == main_project_dir(wire_kiro.package_dir()) == REPO.resolve()
    assert scheduler.PROJECT_DIR == wire_kiro.project_dir()
    assert (wire_kiro.project_dir() / "pyproject.toml").is_file()


@pytest.mark.parametrize("layout", ["repo/src/orgmcp", "venv/lib/python3.11/site-packages/orgmcp", "a/b/c/d/e/site-packages/orgmcp"])
def test_the_project_directory_of_any_layout_is_the_value_of_main(tmp_path: Path, layout: str) -> None:
    package = (tmp_path / layout).resolve()
    package.mkdir(parents=True)
    assert wire_kiro.project_dir_of(package) == main_project_dir(package)


def test_the_uv_fallback_of_the_command_runs_in_the_value_of_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bin" / "python"))  # no console script beside it
    monkeypatch.setattr(shutil, "which", lambda name: f"/opt/{name}")
    assert scheduler.mcp_server_command() == {
        "command": "/opt/uv", "args": ["--directory", str(main_project_dir(Path(orgmcp.__file__).resolve().parent)), "run", "orgmcp", "mcp"]}
    assert wire_kiro.mcp_locator().command() == scheduler.mcp_server_command()


def test_the_console_script_beside_the_interpreter_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "orgmcp").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bin" / "python"))
    assert scheduler.mcp_server_command() == {"command": str(tmp_path / "bin" / "orgmcp"), "args": ["mcp"]}
