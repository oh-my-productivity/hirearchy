"""Risk 8 of ARCHITECTURE.md (path arithmetic that depends on file depth): the checkout of the uv fallback of the MCP command.

On ``main`` it is ``Path(scheduler.__file__).resolve().parents[2]``. The code that builds the command moved one directory deeper
(``hirearchy/kiro/_mcp_locator.py``), so the directory is computed in the wiring from the ``hirearchy`` package, and these tests prove that the
values are the same, in a checkout and in an installed wheel (whose layout is rebuilt here; a real wheel was built with ``uv build`` and
inspected by hand, see the report of the step)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

import hirearchy
import hirearchy.kiro
import hirearchy.scheduler as scheduler
from hirearchy.app import wire_kiro

REPO = Path(__file__).resolve().parents[4]


def main_project_dir(package: Path) -> Path:
    """The expression of ``main`` (scheduler.py: ``PROJECT_DIR = Path(__file__).resolve().parents[2]``), for a package directory."""
    return (package / "scheduler.py").resolve().parents[2]


def test_the_package_directory_is_the_one_of_the_hirearchy_module() -> None:
    assert wire_kiro.package_dir() == Path(hirearchy.__file__).resolve().parent == Path(scheduler.__file__).resolve().parent.parent  # the package directory of hirearchy.scheduler


def test_the_project_directory_of_the_checkout_is_the_value_of_main() -> None:
    assert wire_kiro.project_dir() == main_project_dir(wire_kiro.package_dir()) == REPO.resolve()
    assert (wire_kiro.project_dir() / "pyproject.toml").is_file()


@pytest.mark.parametrize("layout", ["repo/src/hirearchy", "venv/lib/python3.11/site-packages/hirearchy", "a/b/c/d/e/site-packages/hirearchy"])
def test_the_project_directory_of_any_layout_is_the_value_of_main(tmp_path: Path, layout: str) -> None:
    package = (tmp_path / layout).resolve()
    package.mkdir(parents=True)
    assert wire_kiro.project_dir_of(package) == main_project_dir(package)


def test_the_uv_fallback_of_the_command_runs_in_the_value_of_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bin" / "python"))  # no console script beside it
    monkeypatch.setattr(shutil, "which", lambda name: f"/opt/{name}")
    assert wire_kiro.mcp_locator().command() == {
        "command": "/opt/uv", "args": ["--directory", str(main_project_dir(Path(hirearchy.__file__).resolve().parent)), "run", "hirearchy", "mcp"]}


def test_the_console_script_beside_the_interpreter_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "hirearchy").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bin" / "python"))
    assert wire_kiro.mcp_locator().command() == {"command": str(tmp_path / "bin" / "hirearchy"), "args": ["mcp"]}


def test_the_launcher_ships_inside_the_kiro_package() -> None:
    """The launcher is a script of the ``kiro`` package (not of ``tests/``), so a wheel carries it and ``python -I -S`` can run it."""
    launcher = wire_kiro.launcher()
    script = Path(launcher[3])
    assert launcher == (sys.executable, "-I", "-S", str((Path(hirearchy.kiro.__file__).parent / "_launch.py").resolve()))
    assert script.is_file() and script.parent == wire_kiro.package_dir() / "kiro" and "tests" not in script.parts[len(wire_kiro.package_dir().parts):]
