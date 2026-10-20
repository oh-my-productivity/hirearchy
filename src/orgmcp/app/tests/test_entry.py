"""The way in: ``orgmcp.main`` (the console script ``orgmcp = "orgmcp:main"``, ``python -m orgmcp``) is a thin function over the composition root, and
importing a package of the library (``orgmcp.kernel``, ``orgmcp.telemetry``) loads no other part of the application."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import orgmcp
from orgmcp.app import wire_cli

REPO = Path(__file__).resolve().parents[4]


def test_the_console_script_is_main_of_the_package() -> None:
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {"orgmcp": "orgmcp:main"} and callable(orgmcp.main) and orgmcp.__all__ == ["main"]


def test_main_runs_the_command_line_of_the_composition_root(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []
    monkeypatch.setattr(wire_cli, "run_cli", lambda argv=None: seen.append(argv))
    orgmcp.main(["--root", "/somewhere", "status"])
    orgmcp.main()
    assert seen == [["--root", "/somewhere", "status"], None]


def test_python_dash_m_runs_the_same_program() -> None:
    done = subprocess.run([sys.executable, "-m", "orgmcp", "--help"], capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0 and "usage: orgmcp" in done.stdout, done.stderr


@pytest.mark.parametrize("module", ["orgmcp.kernel", "orgmcp.telemetry"])
def test_importing_a_package_of_the_library_loads_no_other_part_of_the_application(module: str) -> None:
    code = f"import sys, {module}; print(sorted(m for m in ('orgmcp.core', 'orgmcp.app', 'orgmcp.cli') if m in sys.modules))"
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0 and done.stdout.strip() == "[]", done.stderr
