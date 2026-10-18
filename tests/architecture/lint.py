"""RED skeleton (M0)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_lint_imports(config: Path, cwd: Path, pythonpath: Path | None = None) -> subprocess.CompletedProcess[str]:
    raise NotImplementedError


def main(argv: list[str]) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
