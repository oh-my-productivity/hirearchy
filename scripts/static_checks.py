#!/usr/bin/env python3
"""The static checks of the refactor, in one place (used by scripts/check.sh and tests/test_static_checks.py).

    uv run python scripts/static_checks.py            # mypy + import-linter
    uv run python scripts/static_checks.py mypy       # only mypy
    uv run python scripts/static_checks.py imports    # only import-linter

* mypy checks with ``strict = true`` (a) every package directory under ``src/orgmcp/`` (a directory with ``__init__.py``: kernel, the
  features, the entry points, app -- a package is a refactored package, ARCHITECTURE.md R10, so nobody has to remember to opt in) and
  (b) the packages listed in ``[tool.mypy] packages`` of pyproject.toml (for a flat legacy module that is made strict early). With
  neither there is nothing to check and the run only proves that mypy works.
* import-linter checks the contracts generated from the packages that exist (``python -m tests.architecture.lint``: layers, private
  modules, kernel independence, ...) and the hand-written ``[[tool.importlinter.contracts]]`` of pyproject.toml. ``lint-imports`` always runs with
  ``--no-cache`` (tests/architecture/lint.py): the cached graph is keyed by mtimes and can say "kept" for a tree that breaks a contract.

Exit status: 0 when everything that ran passed, 1 otherwise, 2 when a tool is not installed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tool(name: str) -> str | None:
    """The executable ``name`` of the interpreter's environment (``uv run`` puts it first), else on PATH."""
    beside = Path(sys.executable).with_name(name)
    return str(beside) if beside.exists() else shutil.which(name)


def discover_packages(source: Path) -> list[str]:
    """``orgmcp.<dir>`` for every package directory of ``source`` (a directory with an __init__.py)."""
    return sorted(f"{source.name}.{d.name}" for d in source.iterdir() if d.is_dir() and (d / "__init__.py").is_file())


def strict_packages() -> list[str]:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    configured = list(config.get("tool", {}).get("mypy", {}).get("packages", []))
    return sorted(set(configured) | set(discover_packages(ROOT / "src" / "orgmcp")))


def run_mypy() -> int:
    exe = tool("mypy")
    if exe is None:
        print("mypy is not installed (uv sync installs the dev dependencies)", file=sys.stderr)
        return 2
    packages = strict_packages()
    if not packages:
        version = subprocess.run([exe, "--version"], capture_output=True, text=True, cwd=ROOT, check=False)
        print(f"mypy: {version.stdout.strip()}; no package is under strict checking yet "
              "(a src/orgmcp/<pkg>/ directory with __init__.py is checked automatically)", flush=True)
        return version.returncode
    print(f"mypy --strict on: {', '.join(packages)}", flush=True)
    code = subprocess.run([exe, *(arg for package in packages for arg in ("-p", package))], cwd=ROOT, check=False).returncode
    tools = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tools").glob("*.py"))  # dev tooling (tools/relocate_tests.py): strict too
    if tools:
        print(f"mypy --strict on: {', '.join(tools)}", flush=True)
        code = max(code, subprocess.run([exe, *tools], cwd=ROOT, check=False).returncode)
    return code


def run_imports() -> int:
    """The generated and the hand-written import contracts: one implementation, ``tests/architecture/lint.py``."""
    return subprocess.run([sys.executable, "-m", "tests.architecture.lint"], cwd=ROOT, check=False).returncode


def main(argv: list[str]) -> int:
    which = argv[0] if argv else "all"
    if which not in ("all", "mypy", "imports"):
        print(__doc__)
        return 2
    codes = []
    if which in ("all", "mypy"):
        codes.append(run_mypy())
    if which in ("all", "imports"):
        codes.append(run_imports())
    return 2 if 2 in codes else int(any(codes))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
