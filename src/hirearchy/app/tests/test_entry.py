"""The way in: ``hirearchy.main`` (the console script ``hirearchy = "hirearchy:main"``, ``python -m hirearchy``) is a thin function over the composition root, and
importing a package of the library (``hirearchy.kernel``, ``hirearchy.telemetry``) loads no other part of the application."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import hirearchy
from hirearchy.app import wire_cli

REPO = Path(__file__).resolve().parents[4]


def test_the_console_script_is_main_of_the_package() -> None:
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {"hirearchy": "hirearchy:main"} and callable(hirearchy.main) and hirearchy.__all__ == ["main"]


def test_main_runs_the_command_line_of_the_composition_root(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []
    monkeypatch.setattr(wire_cli, "run_cli", lambda argv=None: seen.append(argv))
    hirearchy.main(["--root", "/somewhere", "status"])
    hirearchy.main()
    assert seen == [["--root", "/somewhere", "status"], None]


def test_python_dash_m_runs_the_same_program() -> None:
    done = subprocess.run([sys.executable, "-m", "hirearchy", "--help"], capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0 and "usage: hirearchy" in done.stdout, done.stderr


@pytest.mark.parametrize("module", ["hirearchy.kernel", "hirearchy.telemetry"])
def test_importing_a_package_of_the_library_loads_no_other_part_of_the_application(module: str) -> None:
    code = f"import sys, {module}; print(sorted(m for m in ('hirearchy.core', 'hirearchy.app', 'hirearchy.cli') if m in sys.modules))"
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0 and done.stdout.strip() == "[]", done.stderr
