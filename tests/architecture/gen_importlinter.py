"""RED skeleton (M0)."""

from __future__ import annotations

from collections.abc import Mapping

from . import graph
from .checks import Tree

GRAPH: Mapping[str, graph.Package] = {}


def generate(tree: Tree, packages: Mapping[str, graph.Package] = GRAPH) -> str | None:
    raise NotImplementedError
