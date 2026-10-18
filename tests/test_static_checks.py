"""mypy (strict, package by package) and import-linter run as part of the default test run.

Both shell out to ``scripts/static_checks.py``; a test is skipped only when its tool is not installed.
"""

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "static_checks.py"


def run(which: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), which], capture_output=True, text=True, cwd=ROOT, timeout=600)


@pytest.mark.skipif(importlib.util.find_spec("mypy") is None, reason="mypy is not installed (uv sync)")
def test_mypy_strict_on_the_refactored_packages():
    result = run("mypy")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(importlib.util.find_spec("importlinter") is None, reason="import-linter is not installed (uv sync)")
def test_import_contracts_are_kept():
    result = run("imports")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 broken" in result.stdout


def test_tool_versions_are_pinned_exactly():
    dev = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["dependency-groups"]["dev"]
    assert "mypy==2.4.0" in dev and "import-linter==2.15" in dev
