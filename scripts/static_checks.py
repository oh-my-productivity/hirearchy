#!/usr/bin/env python3
"""The static checks of the refactor, in one place (used by scripts/check.sh and tests/test_static_checks.py).

    uv run python scripts/static_checks.py            # mypy + import-linter
    uv run python scripts/static_checks.py mypy       # only mypy
    uv run python scripts/static_checks.py imports    # only import-linter

* mypy checks the packages listed in ``[tool.mypy] packages`` of pyproject.toml with ``strict = true`` (the list is
  empty until the first refactored package exists: then there is nothing to check and the run only proves that mypy works).
* import-linter checks every ``[[tool.importlinter.contracts]]`` of pyproject.toml.

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


def strict_packages() -> list[str]:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return list(config.get("tool", {}).get("mypy", {}).get("packages", []))


def run_mypy() -> int:
    exe = tool("mypy")
    if exe is None:
        print("mypy is not installed (uv sync installs the dev dependencies)", file=sys.stderr)
        return 2
    packages = strict_packages()
    if not packages:
        version = subprocess.run([exe, "--version"], capture_output=True, text=True, cwd=ROOT, check=False)
        print(f"mypy: {version.stdout.strip()}; no package is under strict checking yet "
              "(add it to [tool.mypy] packages in pyproject.toml)", flush=True)
        return version.returncode
    print(f"mypy --strict on: {', '.join(packages)}", flush=True)
    return subprocess.run([exe], cwd=ROOT, check=False).returncode  # targets come from [tool.mypy] packages


def run_imports() -> int:
    exe = tool("lint-imports")
    if exe is None:
        print("import-linter is not installed (uv sync installs the dev dependencies)", file=sys.stderr)
        return 2
    return subprocess.run([exe], cwd=ROOT, check=False).returncode


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
