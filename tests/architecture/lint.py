"""The import contracts, generated and checked: ``uv run python -m tests.architecture.lint`` (ARCHITECTURE.md 8, README "Test").

1. generates ``.importlinter`` (git-ignored) from ``graph.py`` and the packages that exist (``gen_importlinter``) and runs
   ``lint-imports`` on it; when no package of the map exists yet there is nothing to generate and that step is skipped;
2. runs ``lint-imports`` on the hand-written contracts of ``[tool.importlinter]`` in pyproject.toml (what the generator does not derive: ``hirearchy.core`` does not import the entry points).

``lint-imports`` is always given ``--config`` explicitly: a plain ``lint-imports`` would read the generated ``.importlinter`` only,
and always ``--no-cache``: the cached import graph is keyed by file mtimes and can report "kept" for a tree that breaks a contract.
Exit status: 0 when every contract is kept, 1 when one is broken, 2 when import-linter is not installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from . import gen_importlinter
from .checks import Tree
from .paths import REPO, SRC

GENERATED = REPO / ".importlinter"


def executable() -> str | None:
    """lint-imports of the interpreter's environment (``uv run`` puts it first), else on PATH."""
    beside = Path(sys.executable).with_name("lint-imports")
    return str(beside) if beside.exists() else shutil.which("lint-imports")


def run_lint_imports(config: Path, cwd: Path, pythonpath: Path | None = None) -> subprocess.CompletedProcess[str]:
    """``lint-imports --config <config> --no-cache`` in ``cwd``; ``pythonpath`` makes a package outside the environment importable."""
    exe = executable()
    if exe is None:
        return subprocess.CompletedProcess([], 2, "", "import-linter is not installed (uv sync installs the dev dependencies)")
    env = dict(os.environ)
    if pythonpath is not None:
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(pythonpath), env.get("PYTHONPATH", "")]))
    return subprocess.run([exe, "--config", str(config), "--no-cache"], capture_output=True, text=True, cwd=cwd, env=env, check=False)


def main(argv: list[str]) -> int:
    codes = []
    text = gen_importlinter.generate(Tree(SRC))
    if text is None:
        GENERATED.unlink(missing_ok=True)
        print("generated contracts: none apply yet (no package of the architecture map exists)", flush=True)
    else:
        GENERATED.write_text(text, encoding="utf-8")
        print(f"generated contracts: {GENERATED.name}", flush=True)
        codes.append(_show(run_lint_imports(GENERATED, REPO)))
    pyproject = REPO / "pyproject.toml"
    if "importlinter" in tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {}):
        print("hand-written contracts: pyproject.toml [tool.importlinter]", flush=True)
        codes.append(_show(run_lint_imports(pyproject, REPO)))
    return 2 if 2 in codes else int(any(codes))


def _show(result: subprocess.CompletedProcess[str]) -> int:
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
