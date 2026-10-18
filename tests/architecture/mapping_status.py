"""RED skeleton (M0)."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from .checks import Tree


@dataclass
class Row:
    symbol: str


@dataclass
class Result:
    moved: list[Row] = field(default_factory=list)
    unmoved: list[Row] = field(default_factory=list)


def status(package: str, markdown: str, tree: Tree) -> Result:
    raise NotImplementedError


def main(argv: list[str]) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
