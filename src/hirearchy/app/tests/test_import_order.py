"""Import order during the strangler (ARCHITECTURE.md 10.1, risk 9): every module imports on its own, in a fresh interpreter.

``core`` -> ``app.facade`` -> the mixins -> the leaf modules must never close an import cycle. Two orders are tried for
every module of ``src/hirearchy`` (the tests and ``__main__`` excepted):

* *package first*: ``python -c "import hirearchy.<module>"``, as in production (``hirearchy/__init__`` runs first and pulls in the CLI);
* *module first*: the package's ``__init__`` is bypassed (a bare ``hirearchy`` package object stands in for it), so ``<module>`` is the
  first hirearchy module the interpreter loads and nothing imported it "by luck" earlier.
"""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[3]
PACKAGE = SRC / "hirearchy"
PACKAGE_FIRST = "import {module}"
MODULE_FIRST = (
    "import sys, types\n"
    "package = types.ModuleType('hirearchy'); package.__path__ = [{path!r}]; sys.modules['hirearchy'] = package\n"
    "import {module}\n"
)


def modules() -> list[str]:
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        parts = path.relative_to(SRC).with_suffix("").parts
        if "tests" in parts or "__pycache__" in parts or parts == ("hirearchy", "__main__"):
            continue
        found.append(".".join(parts[:-1] if parts[-1] == "__init__" else parts))
    return [m for m in found if m != "hirearchy"]


def import_in_fresh_interpreter(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=SRC.parent, timeout=120, check=False)


def failures(template: str) -> list[str]:
    def attempt(module: str) -> str:
        done = import_in_fresh_interpreter(template.format(module=module, path=str(PACKAGE)))
        return "" if done.returncode == 0 else f"{module}: {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else done.returncode}"

    with ThreadPoolExecutor(max_workers=8) as pool:
        return [line for line in pool.map(attempt, modules()) if line]


def test_the_walk_finds_the_modules() -> None:
    found = modules()
    assert {"hirearchy.core", "hirearchy.kernel", "hirearchy.kernel.api", "hirearchy.telemetry", "hirearchy.services", "hirearchy.app"} <= set(found)
    assert not any(".tests" in m or m.endswith("__main__") for m in found)


def test_import_each_module_in_a_fresh_interpreter() -> None:
    assert not (found := failures(PACKAGE_FIRST)), "\n".join(found)


def test_import_each_module_first_in_a_fresh_interpreter() -> None:
    assert not (found := failures(MODULE_FIRST)), "\n".join(found)


@pytest.mark.parametrize("template", [PACKAGE_FIRST, MODULE_FIRST])
def test_a_failing_import_is_reported(template: str) -> None:
    done = import_in_fresh_interpreter(template.format(module="hirearchy.no_such_module_exists", path=str(PACKAGE)))
    assert done.returncode != 0 and "no_such_module_exists" in done.stderr
