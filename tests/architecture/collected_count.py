"""The collected-test floors (see test_collected_count.py): collect once, count per file, read and write the per-directory ``count.txt``.

    uv run python -m tests.architecture.collected_count            # print the count of every colocated tests directory
    uv run python -m tests.architecture.collected_count --write    # record them (a floor is only ever raised by this command)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from .paths import REPO, SRC

BASELINE = Path(__file__).with_name("baseline_test_count.txt")
FLOOR = "count.txt"


def collect() -> dict[str, int]:
    """Test file (relative to the repository, posix) -> number of collected tests, from one ``pytest --collect-only``."""
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], capture_output=True,
                            text=True, cwd=REPO, timeout=600)
    counts: dict[str, int] = {}
    for line in result.stdout.splitlines():
        if "::" in line and not line.startswith(" "):
            path = line.split("::", 1)[0]
            counts[path] = counts.get(path, 0) + 1
    summary = re.search(r"(\d+) tests? collected", result.stdout)
    if not summary or int(summary.group(1)) != sum(counts.values()):
        raise AssertionError(f"could not read the collection: {result.stdout[-500:]}{result.stderr[-500:]}")
    return counts


def tests_directories() -> list[Path]:
    """Every colocated ``src/orgmcp/**/tests`` package that holds tests."""
    return sorted(d for d in SRC.rglob("tests") if d.is_dir() and (d / "__init__.py").is_file() and any(d.glob("test_*.py")))


def floor_files() -> list[Path]:
    return sorted(SRC.rglob(f"tests/{FLOOR}"))


def directories_without_floor() -> list[str]:
    return [d.relative_to(REPO).as_posix() for d in tests_directories() if not (d / FLOOR).is_file()]


def write() -> None:
    counts = collect()
    for directory in tests_directories():
        prefix = directory.relative_to(REPO).as_posix() + "/"
        current = sum(n for path, n in counts.items() if path.startswith(prefix))
        floor_file = directory / FLOOR
        recorded = int(floor_file.read_text(encoding="utf-8").split()[0]) if floor_file.is_file() else 0
        floor_file.write_text(f"{max(current, recorded)}\n", encoding="utf-8")
        print(f"{prefix}: {max(current, recorded)}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        write()
    else:
        counts = collect()
        for directory in tests_directories():
            prefix = directory.relative_to(REPO).as_posix() + "/"
            print(f"{prefix}: {sum(n for path, n in counts.items() if path.startswith(prefix))}")
